from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests

from .models import BlobSearchResult, BranchRef, Project


class GitLabClient:
    def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v4"
        self.per_page = per_page
        self.session = requests.Session()
        self.session.headers.update(
            {
                "PRIVATE-TOKEN": token,
                "Accept": "application/json",
            }
        )

    def list_projects(self) -> list[Project]:
        params = {"simple": "true", "archived": "false"}
        items = self._get_paginated("/projects", params=params)
        projects: list[Project] = []
        for item in items:
            pid = int(item.get("id", 0))
            if pid == 0:
                continue
            projects.append(
                Project(
                    id=pid,
                    name=str(item.get("name", "")),
                    web_url=str(item.get("web_url", "")),
                )
            )
        return projects

    def get_project_by_path(self, project_path: str) -> Project:
        encoded_path = quote(project_path, safe="")
        response = self.session.get(
            f"{self.api_base}/projects/{encoded_path}",
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text[:300].strip()
            raise requests.HTTPError(
                f"{exc}. url={response.url} detail={detail}"
            ) from exc

        item = response.json()
        pid = int(item.get("id", 0))
        if pid == 0:
            raise ValueError(f"invalid project response for path: {project_path}")
        return Project(
            id=pid,
            name=str(item.get("name", "")),
            web_url=str(item.get("web_url", "")),
        )

    def search_blobs(self, project_id: int, keyword: str, branch: str) -> list[BlobSearchResult]:
        params = {"scope": "blobs", "search": keyword, "ref": branch}
        items = self._get_paginated(f"/projects/{project_id}/search", params=params)
        results: list[BlobSearchResult] = []
        for item in items:
            startline = item.get("startline", 1)
            try:
                startline_int = int(startline)
            except (TypeError, ValueError):
                startline_int = 1

            results.append(
                BlobSearchResult(
                    filename=str(item.get("filename", "")),
                    startline=startline_int,
                    data=str(item.get("data", "")),
                )
            )
        return results

    def list_branches(self, project_id: int) -> list[BranchRef]:
        items = self._get_paginated(f"/projects/{project_id}/repository/branches")
        branches: list[BranchRef] = []
        for item in items:
            name = str(item.get("name", "")).strip()
            if name:
                commit_id = str((item.get("commit") or {}).get("id", "")).strip()
                # Use commit SHA as search ref to avoid server-side issues on special branch names.
                search_ref = commit_id or name
                branches.append(BranchRef(name=name, search_ref=search_ref))
        # keep order while de-duplicating
        uniq: dict[str, BranchRef] = {}
        for br in branches:
            if br.name not in uniq:
                uniq[br.name] = br
        return list(uniq.values())

    def _get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = dict(params or {})
        page = 1
        items: list[dict[str, Any]] = []

        while True:
            request_params = {
                **params,
                "page": page,
                "per_page": self.per_page,
            }
            response = self.session.get(
                f"{self.api_base}{path}",
                params=request_params,
                timeout=30,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                detail = response.text[:300].strip()
                raise requests.HTTPError(
                    f"{exc}. url={response.url} detail={detail}"
                ) from exc

            page_items = response.json()
            if not isinstance(page_items, list):
                break
            items.extend(page_items)

            if len(page_items) < self.per_page:
                break
            page += 1

        return items
