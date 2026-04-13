from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import quote

import requests

from .models import BlobSearchResult, BranchRef, Project


class GitLabClient:
    def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v4"
        self.per_page = per_page
        self._token = token
        self._local = threading.local()

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
                    default_branch=(str(item.get("default_branch", "")).strip() or None),
                )
            )
        return projects

    def get_project_by_path(self, project_path: str) -> Project:
        encoded_path = quote(project_path, safe="")
        response = self._request_get(f"{self.api_base}/projects/{encoded_path}")
        item = response.json()
        pid = int(item.get("id", 0))
        if pid == 0:
            raise ValueError(f"invalid project response for path: {project_path}")
        return Project(
            id=pid,
            name=str(item.get("name", "")),
            web_url=str(item.get("web_url", "")),
            default_branch=(str(item.get("default_branch", "")).strip() or None),
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
            response = self._request_get(f"{self.api_base}{path}", params=request_params)
            page_items = response.json()
            if not isinstance(page_items, list):
                break
            items.extend(page_items)

            if len(page_items) < self.per_page:
                break
            page += 1

        return items

    def _get_session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "PRIVATE-TOKEN": self._token,
                    "Accept": "application/json",
                }
            )
            self._local.session = session
        return session

    def _request_get(self, url: str, params: dict[str, Any] | None = None) -> requests.Response:
        retries = 3
        backoff = 0.5
        session = self._get_session()
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                response = session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response
            except requests.HTTPError as exc:
                response = exc.response
                status_code = response.status_code if response is not None else None
                if status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(backoff * (2**attempt))
                    last_exc = exc
                    continue
                detail = response.text[:300].strip() if response is not None else ""
                raise requests.HTTPError(
                    f"{exc}. url={response.url if response is not None else url} detail={detail}"
                ) from exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt < retries - 1:
                    time.sleep(backoff * (2**attempt))
                    last_exc = exc
                    continue
                raise exc

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("request failed without exception")
