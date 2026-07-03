from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from tqdm import tqdm

from .excel_writer import write_results
from .gitlab_api import GitLabClient
from .models import BranchRef, Project, SearchResult

SUPPORTED_SEARCH_TARGETS = ("code", "commit")


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
    targets: list[str] = field(default_factory=lambda: ["code"])


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


def build_commit_url(project_url: str, commit_id: str) -> str:
    if not commit_id:
        return project_url
    return f"{project_url}/-/commit/{quote(commit_id, safe='')}"


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


def build_commit_search_task_results(
    client: GitLabClient, project: Project, branch_ref: BranchRef, words: list[str]
) -> list[SearchResult]:
    commits = client.list_commits(project_id=project.id, ref_name=branch_ref.name)
    normalized_words = [(word, word.lower()) for word in words]
    results: list[SearchResult] = []
    for commit in commits:
        message = commit.message
        normalized_message = message.lower()
        commit_url = commit.web_url or build_commit_url(project.web_url, commit.commit_id)
        for word, normalized_word in normalized_words:
            if normalized_word not in normalized_message:
                continue
            results.append(
                SearchResult(
                    word=word,
                    branch=branch_ref.name,
                    project_id=project.id,
                    project_name=project.name,
                    project_url=project.web_url,
                    file_name=commit.short_id or commit.commit_id,
                    line_url=commit_url,
                    data=message,
                    result_type="commit",
                    commit_id=commit.commit_id,
                    commit_short_id=commit.short_id,
                    commit_title=commit.title,
                    commit_author_name=commit.author_name,
                    commit_author_email=commit.author_email,
                    commit_authored_date=commit.authored_date,
                    commit_committed_date=commit.committed_date,
                    commit_url=commit_url,
                    commit_message=message,
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


def _resolve_branch_refs(client: GitLabClient, project: Project, request: SearchRequest) -> list[BranchRef]:
    if request.all_branches:
        return client.list_branches(project.id)

    branch_name = request.branch or project.default_branch or "master"
    return [BranchRef(name=branch_name, search_ref=branch_name)]


def normalize_search_targets(targets: list[str] | None) -> list[str]:
    if not targets:
        return ["code"]
    normalized: list[str] = []
    for target in targets:
        target = target.strip().lower()
        if not target:
            continue
        if target not in SUPPORTED_SEARCH_TARGETS:
            raise ValueError(f"unsupported search target: {target}")
        normalized.append(target)
    return list(dict.fromkeys(normalized)) or ["code"]


def execute_search(request: SearchRequest) -> SearchExecutionResult:
    client = GitLabClient(base_url=request.base_url, token=request.token)
    projects = _resolve_projects(client, request)
    targets = normalize_search_targets(request.targets)

    code_tasks: list[tuple[Project, BranchRef, str]] = []
    commit_tasks: list[tuple[Project, BranchRef]] = []
    for project in projects:
        branch_refs = _resolve_branch_refs(client, project, request)
        if not branch_refs:
            continue

        for branch_ref in branch_refs:
            if "code" in targets:
                for word in request.words:
                    code_tasks.append((project, branch_ref, word))
            if "commit" in targets:
                commit_tasks.append((project, branch_ref))

    all_results: list[SearchResult] = []
    failed_tasks = 0
    successful_tasks = 0

    with ThreadPoolExecutor(max_workers=request.workers) as executor:
        future_to_task = {
            executor.submit(build_search_task_results, client, project, branch_ref, word): (project, branch_ref, word)
            for project, branch_ref, word in code_tasks
        }
        future_to_task.update(
            {
                executor.submit(build_commit_search_task_results, client, project, branch_ref, request.words): (
                    project,
                    branch_ref,
                    "commit",
                )
                for project, branch_ref in commit_tasks
            }
        )
        with tqdm(
            total=len(future_to_task),
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
            item.result_type,
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
