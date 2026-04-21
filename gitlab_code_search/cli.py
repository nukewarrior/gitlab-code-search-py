from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlparse

from . import __version__
from .serve import ServeApplication, ServeConfig, StartupError
from .search_service import SearchRequest, build_line_url, execute_search


logger = logging.getLogger("gcs")
SUPPORTED_OUTPUT_FORMATS = ("xlsx", "csv", "json")


def configure_stdio_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except ValueError:
            continue


def parse_words(words_args: Iterable[str]) -> list[str]:
    words: list[str] = []
    for raw in words_args:
        parts = [item.strip() for item in raw.split(",")]
        for part in parts:
            if part:
                words.append(part)
    # keep insertion order while de-duplicating
    return list(dict.fromkeys(words))

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


def parse_non_empty_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not str(path).strip():
        raise argparse.ArgumentTypeError("路径不能为空。")
    return path


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

    try:
        execution = execute_search(
            SearchRequest(
                base_url=base_url,
                token=args.token,
                words=words,
                output_formats=output_formats,
                branch=args.branch,
                all_branches=args.all_branches,
                workers=args.workers,
                no_progress=args.no_progress,
                project_path=project_path,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("搜索失败: %s", exc)
        return 1

    logger.info(
        "搜索完成：任务成功=%s 失败=%s 命中=%s 导出格式=%s",
        execution.successful_tasks,
        execution.failed_tasks,
        len(execution.results),
        ",".join(output_formats),
    )
    for output_path in execution.output_paths:
        logger.info("结果文件: %s", output_path)
    return 0


def run_serve(args: argparse.Namespace) -> int:
    try:
        app = ServeApplication(
            ServeConfig(
                workdir=args.workdir,
                admin_token=args.admin_token,
                host=args.host,
                port=args.port,
                gitlab_url=args.gitlab_url,
                workers=args.workers,
            )
        )
    except StartupError as exc:
        logger.error(str(exc))
        return 2

    app.serve_forever()
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

    serve_parser = subparsers.add_parser("serve", help="启动本地 Web 服务。")
    serve_parser.add_argument("--workdir", required=True, type=parse_non_empty_path, help="服务工作目录。")
    serve_parser.add_argument("--admin-token", required=True, help="管理员 GitLab PAT。")
    serve_parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1。")
    serve_parser.add_argument("--port", type=parse_positive_int, default=8765, help="监听端口，默认 8765。")
    serve_parser.add_argument("--gitlab-url", help="默认 GitLab 地址。首次启动建议显式传入。")
    serve_parser.add_argument(
        "--workers",
        type=parse_positive_int,
        default=8,
        help="后台搜索 worker 数量，默认 8。",
    )
    serve_parser.set_defaults(func=run_serve)

    return parser


def main() -> int:
    configure_stdio_encoding()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    parser = create_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
