from __future__ import annotations

import hashlib
import json
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .credential_store import LocalCredentialStore
from .gitlab_api import GitLabClient
from .search_service import SearchRequest, execute_search
from .serve_store import LOCAL_CREDENTIAL_BACKEND, ServeStore, utc_now
from .web_ui import build_app_html


logger = logging.getLogger("gcs.serve")


@dataclass
class ServeConfig:
    workdir: Path
    admin_token: str
    host: str
    port: int
    gitlab_url: str | None
    workers: int


class StartupError(RuntimeError):
    pass


class ServeApplication:
    def __init__(self, config: ServeConfig) -> None:
        self.config = config
        self.store = ServeStore(config.workdir)
        self.store.ensure_initialized()
        self.credentials = LocalCredentialStore(self.store)
        migrated, previous_backend, invalidated_sessions = self.store.ensure_local_credential_backend()
        if migrated:
            self._safe_audit(
                user_identity=None,
                session_id=None,
                action="credential_backend_migrated",
                target_type="settings",
                target_id="credential_backend",
                summary=f"{previous_backend or 'unset'} -> {LOCAL_CREDENTIAL_BACKEND}; invalidated_sessions={invalidated_sessions}",
                status="success",
                remote_addr=None,
                user_agent=None,
            )
        self.store.mark_unfinished_jobs_interrupted()
        self.executor = ThreadPoolExecutor(max_workers=max(2, config.workers))
        self._bootstrap_admin()

    def serve_forever(self) -> None:
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "gcs-serve/0.1"

            def do_GET(self) -> None:  # noqa: N802
                app.handle_request(self)

            def do_POST(self) -> None:  # noqa: N802
                app.handle_request(self)

            def do_PUT(self) -> None:  # noqa: N802
                app.handle_request(self)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                logger.info("%s - %s", self.address_string(), format % args)

        with ThreadingHTTPServer((self.config.host, self.config.port), Handler) as server:
            logger.info("GCS serve listening on http://%s:%s", self.config.host, self.config.port)
            server.serve_forever()

    def _bootstrap_admin(self) -> None:
        stored_admin_identity = self.store.get_setting("admin_identity")
        stored_admin_gitlab_url = self.store.get_setting("admin_gitlab_url")
        resolved_gitlab_url = self.config.gitlab_url or stored_admin_gitlab_url or self.store.get_setting("default_gitlab_url")
        if not resolved_gitlab_url:
            raise StartupError("首次启动 serve 必须通过 --gitlab-url 指定 GitLab 地址。")
        if stored_admin_gitlab_url and self.config.gitlab_url and self.config.gitlab_url != stored_admin_gitlab_url:
            raise StartupError("当前 workdir 已绑定另一个 GitLab 地址，不能在同一 workdir 下切换管理员实例地址。")

        admin_client = GitLabClient(base_url=resolved_gitlab_url, token=self.config.admin_token)
        admin_user = admin_client.get_current_user()
        admin_identity = self._build_identity(resolved_gitlab_url, admin_user.id)

        if stored_admin_identity and stored_admin_identity != admin_identity:
            self._safe_audit(
                user_identity=None,
                session_id=None,
                action="serve_start_rejected",
                target_type="admin",
                target_id=admin_identity,
                summary="workdir already locked to another administrator identity",
                status="failed",
                remote_addr=None,
                user_agent=None,
            )
            raise StartupError("当前 workdir 已绑定到另一个管理员账号，拒绝使用新的管理员 PAT 启动。")

        credential_key = self._credential_key(admin_identity)
        self.credentials.set_secret(credential_key, self.config.admin_token)
        self.store.upsert_user(
            identity=admin_identity,
            gitlab_url=resolved_gitlab_url,
            display_name=admin_user.name or admin_user.username,
            is_admin=True,
            credential_key=credential_key,
        )
        self.store.set_setting("admin_identity", admin_identity)
        self.store.set_setting("admin_gitlab_url", resolved_gitlab_url)
        if self.config.gitlab_url:
            self.store.set_setting("default_gitlab_url", self.config.gitlab_url)

    def _credential_key(self, identity: str) -> str:
        workdir_hash = hashlib.sha1(str(self.config.workdir).encode("utf-8")).hexdigest()[:12]
        return f"gcs:{workdir_hash}:{identity}"

    @staticmethod
    def _build_identity(gitlab_url: str, user_id: int) -> str:
        return f"{gitlab_url.rstrip('/')}:user:{user_id}"

    def handle_request(self, request: BaseHTTPRequestHandler) -> None:
        parsed = urlparse(request.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._respond_html(
                request,
                build_app_html(default_gitlab_url=self.store.get_setting("default_gitlab_url") or self.config.gitlab_url or ""),
            )
            return

        if not parsed.path.startswith("/api/"):
            self._respond_json(request, HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        try:
            self._dispatch_api(request, parsed)
        except StartupError as exc:
            self._respond_json(request, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except PermissionError as exc:
            self._respond_json(request, HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except FileNotFoundError as exc:
            self._respond_json(request, HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            logger.exception("serve request failed")
            self._respond_json(request, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _dispatch_api(self, request: BaseHTTPRequestHandler, parsed) -> None:
        path = parsed.path
        method = request.command
        body = self._read_json_body(request) if method in {"POST", "PUT"} else {}
        params = parse_qs(parsed.query)

        if path == "/api/auth/login" and method == "POST":
            self._handle_login(request, body)
            return
        if path == "/api/auth/logout" and method == "POST":
            self._handle_logout(request)
            return

        user_ctx = self._require_session(request)

        if path == "/api/me" and method == "GET":
            self._respond_json(request, HTTPStatus.OK, {"user": user_ctx["user"]})
            return
        if path == "/api/projects" and method == "GET":
            self._handle_projects(request, user_ctx, params)
            return
        if path == "/api/jobs" and method == "GET":
            self._handle_list_jobs(request, user_ctx)
            return
        if path == "/api/jobs" and method == "POST":
            self._handle_create_job(request, user_ctx, body)
            return
        if path.startswith("/api/jobs/") and path.endswith("/rerun") and method == "POST":
            job_id = path.split("/")[3]
            self._handle_rerun_job(request, user_ctx, job_id)
            return
        if path.startswith("/api/jobs/") and path.endswith("/cancel") and method == "POST":
            job_id = path.split("/")[3]
            self._handle_cancel_job(request, user_ctx, job_id)
            return
        if path.startswith("/api/jobs/") and path.endswith("/results") and method == "GET":
            job_id = path.split("/")[3]
            self._handle_job_results(request, user_ctx, job_id, params)
            return
        if path.startswith("/api/jobs/") and "/exports/" in path and method == "GET":
            parts = path.split("/")
            job_id = parts[3]
            fmt = parts[5]
            self._handle_download_export(request, user_ctx, job_id, fmt)
            return
        if path.startswith("/api/jobs/") and method == "GET":
            job_id = path.split("/")[3]
            self._handle_get_job(request, user_ctx, job_id)
            return
        if path == "/api/admin/settings" and method == "GET":
            self._require_admin(user_ctx)
            self._respond_json(request, HTTPStatus.OK, {"settings": self._settings_payload()})
            return
        if path == "/api/admin/settings" and method == "PUT":
            self._require_admin(user_ctx)
            self._handle_update_settings(request, user_ctx, body)
            return
        if path == "/api/admin/audit-logs" and method == "GET":
            self._require_admin(user_ctx)
            self._handle_audit_logs(request)
            return

        self._respond_json(request, HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _settings_payload(self) -> dict[str, Any]:
        return {
            "workdir": str(self.config.workdir),
            "db_path": str(self.store.db_path),
            "exports_dir": str(self.store.exports_dir),
            "host": self.config.host,
            "port": self.config.port,
            "workers": self.config.workers,
            "default_gitlab_url": self.store.get_setting("default_gitlab_url") or "",
            "admin_identity": self.store.get_setting("admin_identity") or "",
        }

    def _handle_login(self, request: BaseHTTPRequestHandler, body: dict[str, Any]) -> None:
        token = str(body.get("token", "")).strip()
        gitlab_url = str(body.get("gitlab_url", "")).strip() or self.store.get_setting("default_gitlab_url") or ""
        if not token:
            raise StartupError("token 不能为空。")
        if not gitlab_url:
            raise StartupError("未提供 GitLab 地址，且服务也没有默认 GitLab 地址。")

        client = GitLabClient(base_url=gitlab_url, token=token)
        user = client.get_current_user()
        identity = self._build_identity(gitlab_url, user.id)
        admin_identity = self.store.get_setting("admin_identity") or ""
        is_admin = identity == admin_identity
        credential_key = self._credential_key(identity)
        self.credentials.set_secret(credential_key, token)
        self.store.upsert_user(
            identity=identity,
            gitlab_url=gitlab_url,
            display_name=user.name or user.username,
            is_admin=is_admin,
            credential_key=credential_key,
        )
        session_id = secrets.token_urlsafe(32)
        self.store.create_session(session_id, identity)
        self.store.add_audit_log(
            user_identity=identity,
            session_id=session_id,
            action="login",
            target_type="session",
            target_id=session_id,
            summary="user login",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self._respond_json(
            request,
            HTTPStatus.OK,
            {
                "user": {
                    "identity": identity,
                    "display_name": user.name or user.username,
                    "gitlab_url": gitlab_url,
                    "is_admin": is_admin,
                }
            },
            cookies={"gcs_session": session_id},
        )

    def _handle_logout(self, request: BaseHTTPRequestHandler) -> None:
        session_id = self._session_id_from_request(request)
        session = self.store.get_session(session_id) if session_id else None
        if session_id:
            self.store.deactivate_session(session_id)
        if session is not None:
            self.store.add_audit_log(
                user_identity=session.owner_identity,
                session_id=session_id,
                action="logout",
                target_type="session",
                target_id=session_id,
                summary="user logout",
                status="success",
                remote_addr=request.client_address[0] if request.client_address else None,
                user_agent=request.headers.get("User-Agent"),
            )
        self._respond_json(request, HTTPStatus.OK, {"ok": True}, cookies={"gcs_session": ""}, expire_cookie=True)

    def _handle_projects(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], params: dict[str, list[str]]) -> None:
        query = params.get("q", [""])[0].strip().lower()
        gitlab_url = params.get("gitlab_url", [""])[0].strip() or user_ctx["user"]["gitlab_url"]
        token = self._user_token(user_ctx)
        client = GitLabClient(base_url=gitlab_url, token=token)
        projects = client.list_projects()
        items = []
        for project in projects:
            if query and query not in f"{project.name} {project.web_url}".lower():
                continue
            items.append({"id": project.id, "name": project.name, "web_url": project.web_url})
        self._respond_json(request, HTTPStatus.OK, {"projects": items})

    def _handle_list_jobs(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any]) -> None:
        jobs = self.store.list_jobs_for_user(user_ctx["user"]["identity"])
        self._respond_json(request, HTTPStatus.OK, {"jobs": jobs})

    def _handle_get_job(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], job_id: str) -> None:
        job = self._get_owned_job(user_ctx, job_id)
        self._respond_json(request, HTTPStatus.OK, {"job": job})

    def _handle_create_job(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], body: dict[str, Any]) -> None:
        payload = self._build_job_payload(user_ctx, body)
        self.store.insert_job(payload)
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="create_job",
            target_type="job",
            target_id=payload["id"],
            summary="create search job",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self.executor.submit(self._run_job, payload["id"], user_ctx["user"]["identity"])
        self._respond_json(request, HTTPStatus.CREATED, {"job_id": payload["id"]})

    def _handle_rerun_job(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], job_id: str) -> None:
        original = self._get_owned_job(user_ctx, job_id)
        payload = self._build_job_payload(
            user_ctx,
            {
                "gitlab_url": original["gitlab_url"],
                "project_ids": original["project_ids"],
                "keywords": original["keywords"],
                "branch_mode": original["branch_mode"],
                "branch_name": original.get("branch_name"),
                "formats": original["formats"],
            },
            original_job_id=job_id,
        )
        self.store.insert_job(payload)
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="rerun_job",
            target_type="job",
            target_id=payload["id"],
            summary=f"rerun from {job_id}",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self.executor.submit(self._run_job, payload["id"], user_ctx["user"]["identity"])
        self._respond_json(request, HTTPStatus.CREATED, {"job_id": payload["id"]})

    def _handle_cancel_job(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], job_id: str) -> None:
        job = self._get_owned_job(user_ctx, job_id)
        if job["status"] not in {"queued", "running"}:
            raise StartupError("只有排队中或运行中的任务可以取消。")
        self.store.update_job(
            job_id,
            status="cancelled",
            finished_at=utc_now(),
            failure_reason="cancel requested by user",
        )
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="cancel_job",
            target_type="job",
            target_id=job_id,
            summary="cancel search job",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self._respond_json(request, HTTPStatus.OK, {"ok": True})

    def _handle_job_results(
        self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], job_id: str, params: dict[str, list[str]]
    ) -> None:
        self._get_owned_job(user_ctx, job_id)
        query = params.get("q", [""])[0]
        try:
            page = max(1, int(params.get("page", ["1"])[0] or "1"))
            page_size = max(1, min(200, int(params.get("page_size", ["100"])[0] or "100")))
        except ValueError as exc:
            raise StartupError("分页参数非法。") from exc
        offset = (page - 1) * page_size
        rows, total_count = self.store.list_job_results_page(
            job_id,
            query=query or None,
            limit=page_size,
            offset=offset,
        )
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="view_results",
            target_type="job",
            target_id=job_id,
            summary=f"query={query}; page={page}; page_size={page_size}",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self._respond_json(
            request,
            HTTPStatus.OK,
            {
                "rows": rows,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        )

    def _handle_download_export(
        self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], job_id: str, fmt: str
    ) -> None:
        job = self._get_owned_job(user_ctx, job_id)
        target = None
        for path_str in job["export_paths"]:
            path = Path(path_str)
            if path.suffix.lstrip(".") == fmt:
                target = path
                break
        if target is None or not target.exists():
            raise FileNotFoundError("导出文件不存在。")
        data = target.read_bytes()
        content_types = {
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv; charset=utf-8",
            "json": "application/json; charset=utf-8",
        }
        request.send_response(HTTPStatus.OK)
        request.send_header("Content-Type", content_types.get(fmt, "application/octet-stream"))
        request.send_header("Content-Length", str(len(data)))
        request.send_header("Content-Disposition", f'attachment; filename="{target.name}"')
        request.end_headers()
        request.wfile.write(data)
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="download_export",
            target_type="job",
            target_id=job_id,
            summary=f"format={fmt}",
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )

    def _handle_update_settings(self, request: BaseHTTPRequestHandler, user_ctx: dict[str, Any], body: dict[str, Any]) -> None:
        default_gitlab_url = str(body.get("default_gitlab_url", "")).strip()
        self.store.set_setting("default_gitlab_url", default_gitlab_url)
        self.store.add_audit_log(
            user_identity=user_ctx["user"]["identity"],
            session_id=user_ctx["session_id"],
            action="update_settings",
            target_type="settings",
            target_id="default_gitlab_url",
            summary=default_gitlab_url,
            status="success",
            remote_addr=request.client_address[0] if request.client_address else None,
            user_agent=request.headers.get("User-Agent"),
        )
        self._respond_json(request, HTTPStatus.OK, {"settings": self._settings_payload()})

    def _handle_audit_logs(self, request: BaseHTTPRequestHandler) -> None:
        self._respond_json(request, HTTPStatus.OK, {"logs": self.store.list_audit_logs()})

    def _run_job(self, job_id: str, owner_identity: str) -> None:
        job = self.store.get_job(job_id)
        user = self.store.get_user(owner_identity)
        if job is None or user is None:
            return
        token = self.credentials.get_secret(str(user["credential_key"]))
        if not token:
            self.store.update_job(
                job_id,
                status="failed",
                finished_at=utc_now(),
                failure_reason="missing credential",
            )
            self._safe_audit(
                user_identity=owner_identity,
                session_id=None,
                action="session_restore_failed",
                target_type="user",
                target_id=owner_identity,
                summary="missing persisted credential",
                status="failed",
                remote_addr=None,
                user_agent=None,
            )
            return

        self.store.update_job(job_id, status="running", started_at=utc_now(), progress=5)
        try:
            execution = execute_search(
                SearchRequest(
                    base_url=job["gitlab_url"],
                    token=token,
                    words=job["keywords"],
                    output_formats=job["formats"],
                    all_branches=job["branch_mode"] == "all",
                    branch=job.get("branch_name"),
                    workers=self.config.workers,
                    no_progress=True,
                    output_dir=self.store.exports_dir,
                    base_name=job_id,
                    project_ids=job["project_ids"] or None,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.store.update_job(
                job_id,
                status="failed",
                finished_at=utc_now(),
                failure_reason=str(exc),
                progress=100,
            )
            self._safe_audit(
                user_identity=owner_identity,
                session_id=None,
                action="job_failed",
                target_type="job",
                target_id=job_id,
                summary=str(exc),
                status="failed",
                remote_addr=None,
                user_agent=None,
            )
            return

        result_rows = [
            {
                "word": item.word,
                "branch": item.branch,
                "project_id": item.project_id,
                "project_name": item.project_name,
                "project_url": item.project_url,
                "file_name": item.file_name,
                "line_url": item.line_url,
                "data": item.data,
            }
            for item in execution.results
        ]
        current_job = self.store.get_job(job_id)
        if current_job is not None and current_job["status"] == "cancelled":
            return
        self.store.add_job_results(job_id, result_rows)
        self.store.update_job(
            job_id,
            status="completed",
            finished_at=utc_now(),
            progress=100,
            export_base_name=job_id,
            export_paths=[str(path) for path in execution.output_paths],
        )

    def _build_job_payload(
        self, user_ctx: dict[str, Any], body: dict[str, Any], original_job_id: str | None = None
    ) -> dict[str, Any]:
        keywords = body.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.replace(",", "\n").splitlines() if item.strip()]
        keywords = [str(item).strip() for item in keywords if str(item).strip()]
        if not keywords:
            raise StartupError("请至少提供一个关键字。")
        raw_formats = body.get("formats")
        formats = ["xlsx"] if raw_formats is None else raw_formats
        if isinstance(formats, str):
            formats = [formats]
        formats = [str(item).strip() for item in formats if str(item).strip()]
        if not formats:
            raise StartupError("请至少选择一种导出格式。")
        branch_mode = str(body.get("branch_mode") or "all")
        if branch_mode not in {"default", "specific", "all"}:
            raise StartupError("branch_mode 非法。")
        branch_name = str(body.get("branch_name") or "").strip() or None
        if branch_mode == "specific" and not branch_name:
            raise StartupError("指定分支模式下必须提供 branch_name。")
        return {
            "id": secrets.token_hex(12),
            "owner_identity": user_ctx["user"]["identity"],
            "gitlab_url": str(body.get("gitlab_url") or user_ctx["user"]["gitlab_url"]),
            "project_ids": [int(item) for item in body.get("project_ids") or []],
            "keywords": [str(item) for item in keywords],
            "branch_mode": branch_mode,
            "branch_name": branch_name,
            "formats": [str(item) for item in formats],
            "status": "queued",
            "progress": 0,
            "created_at": utc_now(),
            "started_at": None,
            "finished_at": None,
            "failure_reason": None,
            "export_base_name": None,
            "export_paths": [],
            "original_job_id": original_job_id,
        }

    def _get_owned_job(self, user_ctx: dict[str, Any], job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if job is None:
            raise FileNotFoundError("任务不存在。")
        if job["owner_identity"] != user_ctx["user"]["identity"]:
            raise PermissionError("无权访问该任务。")
        return job

    def _require_admin(self, user_ctx: dict[str, Any]) -> None:
        if not user_ctx["user"]["is_admin"]:
            raise PermissionError("只有管理员可以访问该接口。")

    def _require_session(self, request: BaseHTTPRequestHandler) -> dict[str, Any]:
        session_id = self._session_id_from_request(request)
        if not session_id:
            raise PermissionError("未登录。")
        session = self.store.get_session(session_id)
        if session is None or not session.is_active:
            raise PermissionError("会话不存在或已失效。")
        user_row = self.store.get_user(session.owner_identity)
        if user_row is None:
            raise PermissionError("用户不存在。")
        if not self.credentials.get_secret(str(user_row["credential_key"])):
            self.store.deactivate_session(session_id)
            self._safe_audit(
                user_identity=str(user_row["identity"]),
                session_id=session_id,
                action="session_restore_failed",
                target_type="session",
                target_id=session_id,
                summary="missing persisted credential",
                status="failed",
                remote_addr=request.client_address[0] if request.client_address else None,
                user_agent=request.headers.get("User-Agent"),
            )
            raise PermissionError("会话凭据已失效，请重新登录。")
        self.store.touch_session(session_id)
        return {
            "session_id": session_id,
            "user": {
                "identity": str(user_row["identity"]),
                "gitlab_url": str(user_row["gitlab_url"]),
                "display_name": str(user_row["display_name"]),
                "is_admin": bool(user_row["is_admin"]),
            },
        }

    def _user_token(self, user_ctx: dict[str, Any]) -> str:
        user_row = self.store.get_user(user_ctx["user"]["identity"])
        if user_row is None:
            raise PermissionError("用户不存在。")
        token = self.credentials.get_secret(str(user_row["credential_key"]))
        if not token:
            raise PermissionError("凭据不存在，请重新登录。")
        return token

    @staticmethod
    def _session_id_from_request(request: BaseHTTPRequestHandler) -> str | None:
        raw_cookie = request.headers.get("Cookie")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        morsel = cookie.get("gcs_session")
        return None if morsel is None else morsel.value

    @staticmethod
    def _read_json_body(request: BaseHTTPRequestHandler) -> dict[str, Any]:
        content_length = int(request.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}
        raw = request.rfile.read(content_length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    @staticmethod
    def _respond_html(request: BaseHTTPRequestHandler, html: str) -> None:
        data = html.encode("utf-8")
        request.send_response(HTTPStatus.OK)
        request.send_header("Content-Type", "text/html; charset=utf-8")
        request.send_header("Content-Length", str(len(data)))
        request.end_headers()
        request.wfile.write(data)

    @staticmethod
    def _respond_json(
        request: BaseHTTPRequestHandler,
        status: HTTPStatus,
        payload: dict[str, Any],
        cookies: dict[str, str] | None = None,
        expire_cookie: bool = False,
    ) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request.send_response(status)
        request.send_header("Content-Type", "application/json; charset=utf-8")
        if cookies:
            for name, value in cookies.items():
                cookie_value = f"{name}={value}; Path=/; HttpOnly"
                if expire_cookie:
                    cookie_value += "; Max-Age=0"
                else:
                    cookie_value += "; Max-Age=2592000"
                request.send_header("Set-Cookie", cookie_value)
        request.send_header("Content-Length", str(len(data)))
        request.end_headers()
        request.wfile.write(data)

    def _safe_audit(self, **kwargs: Any) -> None:
        try:
            self.store.add_audit_log(**kwargs)
        except Exception:  # noqa: BLE001
            logger.exception("failed to write audit log")
