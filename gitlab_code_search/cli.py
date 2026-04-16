from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Iterable
from urllib.parse import quote, urlparse

from tqdm import tqdm

from . import __version__
from .gitlab_api import GitLabClient
from .models import BranchRef, Project, SearchResult


logger = logging.getLogger("gcs")
SUPPORTED_OUTPUT_FORMATS = ("xlsx", "csv", "json")


def parse_words(words_args: Iterable[str]) -> list[str]:
    words: list[str] = []
    for raw in words_args:
        parts = [item.strip() for item in raw.split(",")]
        for part in parts:
            if part:
                words.append(part)
    # keep insertion order while de-duplicating
    return list(dict.fromkeys(words))


def build_line_url(project_url: str, branch: str, filename: str, startline: int) -> str:
    encoded_branch = quote(branch, safe="")
    encoded_filename = quote(filename, safe="/")
    return f"{project_url}/-/blob/{encoded_branch}/{encoded_filename}#L{startline}"


def parse_gitlab_input_url(raw_url: str) -> tuple[str, str | None]:
    """
    `-u` 既支持 GitLab 根地址，也支持具体项目地址：
    - https://gitlab.example.com
    - https://gitlab.example.com/group/subgroup/project
    """
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("`-u/--url` 不是合法 URL，请提供完整地址（含 http/https）。")

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    project_path = parsed.path.strip("/")
    if not project_path:
        return base_url, None
    return base_url, project_path


def parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数。") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须大于等于 1。")
    return parsed


def parse_output_formats(format_args: list[str] | None) -> list[str]:
    if not format_args:
        return ["xlsx"]
    formats: list[str] = []
    for raw in format_args:
        for part in raw.split(","):
            fmt = part.strip().lower()
            if not fmt:
                continue
            if fmt not in SUPPORTED_OUTPUT_FORMATS:
                raise ValueError(f"不支持的导出格式: {fmt}，支持: {','.join(SUPPORTED_OUTPUT_FORMATS)}")
            formats.append(fmt)
    if not formats:
        return ["xlsx"]
    # de-duplicate and keep order
    return list(dict.fromkeys(formats))


def _build_search_task_results(
    client: GitLabClient, project: Project, branch_ref: BranchRef, word: str
) -> list[SearchResult]:
    blobs = client.search_blobs(project_id=project.id, keyword=word, branch=branch_ref.search_ref)
    results: list[SearchResult] = []
    for blob in blobs:
        results.append(
            SearchResult(
                word=word,
                branch=branch_ref.name,
                project_id=project.id,
                project_name=project.name,
                project_url=project.web_url,
                file_name=blob.filename,
                line_url=build_line_url(project.web_url, branch_ref.name, blob.filename, blob.startline),
                data=blob.data,
            )
        )
    return results


def run_search(args: argparse.Namespace) -> int:
    words = parse_words(args.words)
    if not words:
        logger.error("`-w/--words` 至少提供一个关键字。")
        return 2

    try:
        base_url, project_path = parse_gitlab_input_url(args.url)
    except ValueError as exc:
        logger.error(str(exc))
        return 2

    try:
        output_formats = parse_output_formats(args.format)
    except ValueError as exc:
        logger.error(str(exc))
        return 2

    client = GitLabClient(base_url=base_url, token=args.token)
    if project_path:
        try:
            project = client.get_project_by_path(project_path)
            projects = [project]
        except Exception as exc:  # noqa: BLE001
            logger.error("获取项目失败: %s", exc)
            return 1
        logger.info("已切换为单仓库模式: %s", project.web_url)
    else:
        try:
            projects = client.list_projects()
        except Exception as exc:  # noqa: BLE001
            logger.error("获取所有项目失败: %s", exc)
            return 1

    logger.info("共获取到 %s 个项目，开始检索...", len(projects))

    # Build task list first so we can run concurrent searches.
    tasks: list[tuple[Project, BranchRef, str]] = []

    for index, project in enumerate(projects, start=1):
        logger.info("进度 %s/%s: %s", index, len(projects), project.name)
        if args.all_branches:
            try:
                branch_refs = client.list_branches(project.id)
            except Exception as exc:  # noqa: BLE001
                logger.error("获取分支失败: project=%s err=%s", project.id, exc)
                continue
            if not branch_refs:
                logger.warning("项目无可用分支，跳过: project=%s", project.id)
                continue
        else:
            branch_name = args.branch or project.default_branch or "master"
            branch_refs = [BranchRef(name=branch_name, search_ref=branch_name)]

        for branch_ref in branch_refs:
            for word in words:
                tasks.append((project, branch_ref, word))

    logger.info(
        "共生成 %s 个检索任务，workers=%s，模式=%s",
        len(tasks),
        args.workers,
        "all-branches" if args.all_branches else "default-branch",
    )

    all_results: list[SearchResult] = []
    failed_tasks = 0
    successful_tasks = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_task = {
            executor.submit(_build_search_task_results, client, project, branch_ref, word): (project, branch_ref, word)
            for project, branch_ref, word in tasks
        }
        with tqdm(
            total=len(tasks),
            desc="检索进度",
            unit="task",
            dynamic_ncols=True,
            disable=args.no_progress,
            leave=True,
        ) as progress:
            for future in as_completed(future_to_task):
                project, branch_ref, word = future_to_task[future]
                try:
                    results = future.result()
                except Exception as exc:  # noqa: BLE001
                    failed_tasks += 1
                    logger.error(
                        "搜索失败: project=%s branch=%s word=%s err=%s",
                        project.id,
                        branch_ref.name,
                        word,
                        exc,
                    )
                    progress.update(1)
                    continue
                successful_tasks += 1
                if results:
                    all_results.extend(results)
                progress.update(1)

    all_results.sort(
        key=lambda item: (
            item.project_id,
            item.branch,
            item.word,
            item.file_name,
            item.line_url,
            item.data,
        )
    )

    try:
        from .excel_writer import write_results

        output_paths = write_results(all_results, formats=output_formats)
    except Exception as exc:  # noqa: BLE001
        logger.error("将内容写入到导出文件失败: %s", exc)
        return 1

    logger.info(
        "搜索完成：任务成功=%s 失败=%s 命中=%s 导出格式=%s",
        successful_tasks,
        failed_tasks,
        len(all_results),
        ",".join(output_formats),
    )
    for output_path in output_paths:
        logger.info("结果文件: %s", output_path)
    return 0


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gcs",
        description="通过关键字搜索 GitLab 所有匹配的项目。",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"gcs {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="执行代码检索并导出 Excel。")
    search_parser.add_argument(
        "-u",
        "--url",
        required=True,
        help="GitLab 根地址或项目地址，例如 https://gitlab.example.com 或 https://gitlab.example.com/group/project",
    )
    search_parser.add_argument("-t", "--token", required=True, help="GitLab 认证 token")
    search_parser.add_argument(
        "-w",
        "--words",
        required=True,
        action="append",
        help='检索关键字。支持多次传入，且每次可逗号分隔，例如 `-w "a,b" -w "c"`。',
    )
    search_parser.add_argument("-b", "--branch", help="检索分支，默认项目主分支")
    search_parser.add_argument(
        "--all-branches",
        action="store_true",
        help="搜索所有分支。开启后会忽略 -b/--branch。",
    )
    search_parser.add_argument(
        "--workers",
        type=parse_positive_int,
        default=8,
        help="并发 worker 数量，默认 8。",
    )
    search_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="关闭并发任务进度条显示。",
    )
    search_parser.add_argument(
        "--format",
        action="append",
        help="导出格式，支持 xlsx,csv,json。可重复或逗号分隔；默认 xlsx。",
    )
    search_parser.set_defaults(func=run_search)

    return parser


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = create_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
