from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable
from urllib.parse import quote, urlparse

from . import __version__
from .gitlab_api import GitLabClient
from .models import BranchRef, SearchResult


logger = logging.getLogger("gcs")


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
    return f"{project_url}/-/blob/{encoded_branch}/{filename}#L{startline}"


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

    client = GitLabClient(base_url=base_url, token=args.token)
    default_branch = args.branch or "master"

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
    all_results: list[SearchResult] = []

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
            branch_refs = [BranchRef(name=default_branch, search_ref=default_branch)]

        for branch_ref in branch_refs:
            branch_name = branch_ref.name
            search_ref = branch_ref.search_ref
            for word in words:
                try:
                    blobs = client.search_blobs(project_id=project.id, keyword=word, branch=search_ref)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "搜索失败: project=%s branch=%s word=%s err=%s",
                        project.id,
                        branch_name,
                        word,
                        exc,
                    )
                    continue

                for blob in blobs:
                    all_results.append(
                        SearchResult(
                            word=word,
                            branch=branch_name,
                            project_id=project.id,
                            project_name=project.name,
                            project_url=project.web_url,
                            file_name=blob.filename,
                            line_url=build_line_url(project.web_url, branch_name, blob.filename, blob.startline),
                            data=blob.data,
                        )
                    )

    try:
        from .excel_writer import write_results_xlsx

        output_path = write_results_xlsx(all_results)
    except Exception as exc:  # noqa: BLE001
        logger.error("将内容写入到 Excel 失败: %s", exc)
        return 1

    logger.info("搜索完成，命中 %s 条，结果文件: %s", len(all_results), output_path)
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
    search_parser.add_argument("-b", "--branch", default="master", help="检索分支，默认 master")
    search_parser.add_argument(
        "--all-branches",
        action="store_true",
        help="搜索所有分支。开启后会忽略 -b/--branch。",
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
