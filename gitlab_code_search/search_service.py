from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from tqdm import tqdm

from .excel_writer import write_results
from .gitlab_api import GitLabClient
from .models import BranchRef, Project, SearchResult


@dataclass
class SearchRequest:
    base_url: str
    token: str
    words: list[str]
    output_formats: list[str]
    branch: str | None = None
    all_branches: bool = False
    workers: int = 8
    no_progress: bool = False
    output_dir: str | Path = "."
    base_name: str | None = None
    project_path: str | None = None
    project_ids: list[int] | None = None


@dataclass
class SearchExecutionResult:
    results: list[SearchResult]
    output_paths: list[Path]
    successful_tasks: int
    failed_tasks: int
    projects: list[Project]


def build_line_url(project_url: str, branch: str, filename: str, startline: int) -> str:
    encoded_branch = quote(branch, safe="")
    encoded_filename = quote(filename, safe="/")
    return f"{project_url}/-/blob/{encoded_branch}/{encoded_filename}#L{startline}"


def build_search_task_results(
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


def _resolve_projects(client: GitLabClient, request: SearchRequest) -> list[Project]:
    if request.project_path:
        return [client.get_project_by_path(request.project_path)]

    projects = client.list_projects()
    if request.project_ids:
        allowed = set(request.project_ids)
        projects = [project for project in projects if project.id in allowed]
    return projects


def execute_search(request: SearchRequest) -> SearchExecutionResult:
    client = GitLabClient(base_url=request.base_url, token=request.token)
    projects = _resolve_projects(client, request)

    tasks: list[tuple[Project, BranchRef, str]] = []
    for project in projects:
        if request.all_branches:
            branch_refs = client.list_branches(project.id)
            if not branch_refs:
                continue
        else:
            branch_name = request.branch or project.default_branch or "master"
            branch_refs = [BranchRef(name=branch_name, search_ref=branch_name)]

        for branch_ref in branch_refs:
            for word in request.words:
                tasks.append((project, branch_ref, word))

    all_results: list[SearchResult] = []
    failed_tasks = 0
    successful_tasks = 0

    with ThreadPoolExecutor(max_workers=request.workers) as executor:
        future_to_task = {
            executor.submit(build_search_task_results, client, project, branch_ref, word): (project, branch_ref, word)
            for project, branch_ref, word in tasks
        }
        with tqdm(
            total=len(tasks),
            desc="检索进度",
            unit="task",
            dynamic_ncols=True,
            disable=request.no_progress,
            leave=True,
        ) as progress:
            for future in as_completed(future_to_task):
                try:
                    results = future.result()
                except Exception:
                    failed_tasks += 1
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
    output_paths = write_results(
        all_results,
        formats=request.output_formats,
        output_dir=request.output_dir,
        base_name=request.base_name,
    )
    return SearchExecutionResult(
        results=all_results,
        output_paths=output_paths,
        successful_tasks=successful_tasks,
        failed_tasks=failed_tasks,
        projects=projects,
    )
