import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gitlab_code_search.cli import create_parser
from gitlab_code_search.credential_store import LocalCredentialStore
from gitlab_code_search.models import AuthenticatedUser, SearchResult
from gitlab_code_search.search_service import SearchExecutionResult
from gitlab_code_search.serve import ServeApplication, ServeConfig, StartupError
from gitlab_code_search.serve_store import LOCAL_CREDENTIAL_BACKEND, ServeStore
from gitlab_code_search.web_ui import build_app_html


class DummyRequest:
    def __init__(self, cookie: str | None = None) -> None:
        self.client_address = ("127.0.0.1", 8765)
        self.headers = {"User-Agent": "tests"}
        if cookie:
            self.headers["Cookie"] = cookie


class ServeParserTests(unittest.TestCase):
    def test_serve_parser_requires_workdir_and_admin_token(self) -> None:
        parser = create_parser()
        args = parser.parse_args(
            [
                "serve",
                "--workdir",
                "/tmp/gcs-workdir",
                "--admin-token",
                "glpat-admin",
            ]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)
        self.assertEqual(args.workers, 8)


class ServeBootstrapTests(unittest.TestCase):
    def test_local_credential_store_crud(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ServeStore(tmpdir)
            store.ensure_initialized()
            credentials = LocalCredentialStore(store)

            credentials.set_secret("user-1", "glpat-1")
            self.assertEqual(credentials.get_secret("user-1"), "glpat-1")

            credentials.set_secret("user-1", "glpat-2")
            self.assertEqual(credentials.get_secret("user-1"), "glpat-2")

            credentials.delete_secret("user-1")
            self.assertIsNone(credentials.get_secret("user-1"))

    def test_store_initialization_creates_sqlite_and_exports_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ServeStore(tmpdir)
            store.ensure_initialized()
            self.assertTrue((Path(tmpdir) / "gcs.sqlite3").exists())
            self.assertTrue((Path(tmpdir) / "exports").exists())
            with store._connect() as conn:
                tables = {
                    row["name"]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
            self.assertIn("credentials", tables)

    def test_admin_identity_is_locked_per_workdir(self) -> None:
        token_map = {
            "admin-v1": AuthenticatedUser(id=1, username="admin", name="Admin"),
            "admin-v2": AuthenticatedUser(id=1, username="admin", name="Admin"),
            "other-admin": AuthenticatedUser(id=2, username="other", name="Other"),
        }

        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return token_map[self.token]

        with tempfile.TemporaryDirectory() as tmpdir, patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
            app1 = ServeApplication(
                ServeConfig(
                    workdir=Path(tmpdir),
                    admin_token="admin-v1",
                    host="127.0.0.1",
                    port=8765,
                    gitlab_url="https://gitlab.example.com",
                    workers=2,
                )
            )
            self.assertEqual(
                app1.credentials.get_secret(app1._credential_key("https://gitlab.example.com:user:1")),
                "admin-v1",
            )
            app1.executor.shutdown(wait=False)

            app2 = ServeApplication(
                ServeConfig(
                    workdir=Path(tmpdir),
                    admin_token="admin-v2",
                    host="127.0.0.1",
                    port=8765,
                    gitlab_url="https://gitlab.example.com",
                    workers=2,
                )
            )
            self.assertEqual(
                app2.credentials.get_secret(app2._credential_key("https://gitlab.example.com:user:1")),
                "admin-v2",
            )
            app2.executor.shutdown(wait=False)

            with self.assertRaises(StartupError):
                app3 = ServeApplication(
                    ServeConfig(
                        workdir=Path(tmpdir),
                        admin_token="other-admin",
                        host="127.0.0.1",
                        port=8765,
                        gitlab_url="https://gitlab.example.com",
                        workers=2,
                    )
                )
                app3.executor.shutdown(wait=False)

    def test_existing_sessions_are_invalidated_when_backend_is_migrated(self) -> None:
        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return AuthenticatedUser(id=1, username="admin", name="Admin")

        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_store = ServeStore(tmpdir)
            legacy_store.ensure_initialized()
            legacy_store.upsert_user(
                identity="https://gitlab.example.com:user:9",
                gitlab_url="https://gitlab.example.com",
                display_name="Legacy",
                is_admin=False,
                credential_key="legacy-key",
            )
            legacy_store.create_session("legacy-session", "https://gitlab.example.com:user:9")

            with patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
                app = ServeApplication(
                    ServeConfig(
                        workdir=Path(tmpdir),
                        admin_token="admin-token",
                        host="127.0.0.1",
                        port=8765,
                        gitlab_url="https://gitlab.example.com",
                        workers=2,
                    )
                )
                session = app.store.get_session("legacy-session")
                self.assertIsNotNone(session)
                self.assertFalse(session.is_active)
                self.assertEqual(app.store.get_setting("credential_backend"), LOCAL_CREDENTIAL_BACKEND)
                audit_logs = app.store.list_audit_logs()
                self.assertTrue(any(log["action"] == "credential_backend_migrated" for log in audit_logs))
                app.executor.shutdown(wait=False)

    def test_build_job_payload_requires_keywords_and_formats(self) -> None:
        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return AuthenticatedUser(id=1, username="admin", name="Admin")

        with tempfile.TemporaryDirectory() as tmpdir, patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
            app = ServeApplication(
                ServeConfig(
                    workdir=Path(tmpdir),
                    admin_token="glpat-admin",
                    host="127.0.0.1",
                    port=8765,
                    gitlab_url="https://gitlab.example.com",
                    workers=2,
                )
            )
            user_ctx = {
                "user": {
                    "identity": "https://gitlab.example.com:user:1",
                    "gitlab_url": "https://gitlab.example.com",
                }
            }
            with self.assertRaises(StartupError):
                app._build_job_payload(user_ctx, {"keywords": "   ", "formats": ["xlsx"]})
            with self.assertRaises(StartupError):
                app._build_job_payload(user_ctx, {"keywords": "foo", "formats": []})
            payload = app._build_job_payload(
                user_ctx,
                {
                    "keywords": "foo, bar\nbaz",
                    "formats": ["xlsx", "json"],
                    "branch_mode": "specific",
                    "branch_name": "main",
                },
            )
            self.assertEqual(payload["keywords"], ["foo", "bar", "baz"])
            self.assertEqual(payload["formats"], ["xlsx", "json"])
            self.assertEqual(payload["branch_name"], "main")
            default_payload = app._build_job_payload(user_ctx, {"keywords": "foo", "formats": ["xlsx"]})
            self.assertEqual(default_payload["branch_mode"], "all")
            self.assertIsNone(default_payload["branch_name"])
            app.executor.shutdown(wait=False)

    def test_login_persists_user_credential_and_session_survives_restart(self) -> None:
        token_map = {
            "admin-token": AuthenticatedUser(id=1, username="admin", name="Admin"),
            "user-token": AuthenticatedUser(id=2, username="user", name="User"),
        }

        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return token_map[self.token]

        with tempfile.TemporaryDirectory() as tmpdir, patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
            captured_payloads: list[dict[str, object]] = []

            with patch("gitlab_code_search.serve.ServeApplication._respond_json") as respond_json:
                def remember_response(request, status, payload, cookies=None, expire_cookie=False):
                    captured_payloads.append(
                        {
                            "status": status,
                            "payload": payload,
                            "cookies": cookies or {},
                            "expire_cookie": expire_cookie,
                        }
                    )

                respond_json.side_effect = remember_response
                app1 = ServeApplication(
                    ServeConfig(
                        workdir=Path(tmpdir),
                        admin_token="admin-token",
                        host="127.0.0.1",
                        port=8765,
                        gitlab_url="https://gitlab.example.com",
                        workers=2,
                    )
                )
                app1._handle_login(
                    DummyRequest(),
                    {"token": "user-token", "gitlab_url": "https://gitlab.example.com"},
                )

            login_response = captured_payloads[-1]
            session_id = str(login_response["cookies"]["gcs_session"])
            user_identity = "https://gitlab.example.com:user:2"
            self.assertEqual(
                app1.credentials.get_secret(app1._credential_key(user_identity)),
                "user-token",
            )
            app1.executor.shutdown(wait=False)

            with patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
                app2 = ServeApplication(
                    ServeConfig(
                        workdir=Path(tmpdir),
                        admin_token="admin-token",
                        host="127.0.0.1",
                        port=8765,
                        gitlab_url="https://gitlab.example.com",
                        workers=2,
                    )
                )
                user_ctx = app2._require_session(DummyRequest(cookie=f"gcs_session={session_id}"))
                self.assertEqual(user_ctx["user"]["identity"], user_identity)
                self.assertEqual(app2._user_token(user_ctx), "user-token")
                app2.executor.shutdown(wait=False)

    def test_missing_persisted_credential_invalidates_session(self) -> None:
        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return AuthenticatedUser(id=1, username="admin", name="Admin")

        with tempfile.TemporaryDirectory() as tmpdir, patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
            app = ServeApplication(
                ServeConfig(
                    workdir=Path(tmpdir),
                    admin_token="admin-token",
                    host="127.0.0.1",
                    port=8765,
                    gitlab_url="https://gitlab.example.com",
                    workers=2,
                )
            )
            user_identity = "https://gitlab.example.com:user:7"
            credential_key = app._credential_key(user_identity)
            app.store.upsert_user(
                identity=user_identity,
                gitlab_url="https://gitlab.example.com",
                display_name="User Seven",
                is_admin=False,
                credential_key=credential_key,
            )
            app.credentials.set_secret(credential_key, "glpat-user-7")
            app.store.create_session("session-7", user_identity)
            app.credentials.delete_secret(credential_key)

            with self.assertRaises(PermissionError):
                app._require_session(DummyRequest(cookie="gcs_session=session-7"))

            session = app.store.get_session("session-7")
            self.assertIsNotNone(session)
            self.assertFalse(session.is_active)
            app.executor.shutdown(wait=False)

    def test_run_job_uses_local_credentials_and_completes(self) -> None:
        class FakeGitLabClient:
            def __init__(self, base_url: str, token: str, per_page: int = 50) -> None:
                self.base_url = base_url
                self.token = token

            def get_current_user(self) -> AuthenticatedUser:
                return AuthenticatedUser(id=1, username="admin", name="Admin")

        captured_request = {}

        def fake_execute_search(request):
            captured_request["token"] = request.token
            return SearchExecutionResult(
                results=[
                    SearchResult(
                        word="foo",
                        branch="main",
                        project_id=1,
                        project_name="proj",
                        project_url="https://gitlab.example.com/proj",
                        file_name="a.py",
                        line_url="https://gitlab.example.com/proj/-/blob/main/a.py#L1",
                        data="foo",
                    )
                ],
                output_paths=[Path(tmpdir) / "exports" / "job-1.xlsx"],
                successful_tasks=1,
                failed_tasks=0,
                projects=[],
            )

        with tempfile.TemporaryDirectory() as tmpdir, patch("gitlab_code_search.serve.GitLabClient", FakeGitLabClient):
            app = ServeApplication(
                ServeConfig(
                    workdir=Path(tmpdir),
                    admin_token="admin-token",
                    host="127.0.0.1",
                    port=8765,
                    gitlab_url="https://gitlab.example.com",
                    workers=2,
                )
            )
            user_identity = "https://gitlab.example.com:user:1"
            credential_key = app._credential_key(user_identity)
            app.credentials.set_secret(credential_key, "glpat-user")
            app.store.upsert_user(
                identity=user_identity,
                gitlab_url="https://gitlab.example.com",
                display_name="Admin",
                is_admin=True,
                credential_key=credential_key,
            )
            app.store.insert_job(
                {
                    "id": "job-1",
                    "owner_identity": user_identity,
                    "gitlab_url": "https://gitlab.example.com",
                    "project_ids": [],
                    "keywords": ["foo"],
                    "branch_mode": "default",
                    "branch_name": None,
                    "formats": ["xlsx"],
                    "status": "queued",
                    "progress": 0,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": None,
                    "finished_at": None,
                    "failure_reason": None,
                    "export_base_name": None,
                    "export_paths": [],
                    "original_job_id": None,
                }
            )

            with patch("gitlab_code_search.serve.execute_search", side_effect=fake_execute_search):
                app._run_job("job-1", user_identity)

            job = app.store.get_job("job-1")
            self.assertEqual(captured_request["token"], "glpat-user")
            self.assertIsNotNone(job)
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["result_count"], 1)
            app.executor.shutdown(wait=False)

    def test_store_reports_result_count_for_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ServeStore(tmpdir)
            store.ensure_initialized()
            store.insert_job(
                {
                    "id": "job-1",
                    "owner_identity": "user-1",
                    "gitlab_url": "https://gitlab.example.com",
                    "project_ids": [],
                    "keywords": ["foo"],
                    "branch_mode": "default",
                    "branch_name": None,
                    "formats": ["xlsx"],
                    "status": "completed",
                    "progress": 100,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": None,
                    "finished_at": None,
                    "failure_reason": None,
                    "export_base_name": None,
                    "export_paths": [],
                    "original_job_id": None,
                }
            )
            store.add_job_results(
                "job-1",
                [
                    {
                        "word": "foo",
                        "branch": "main",
                        "project_id": 1,
                        "project_name": "proj",
                        "project_url": "https://gitlab.example.com/proj",
                        "file_name": "a.py",
                        "line_url": "https://gitlab.example.com/proj/-/blob/main/a.py#L1",
                        "data": "foo",
                    },
                    {
                        "word": "foo",
                        "branch": "main",
                        "project_id": 1,
                        "project_name": "proj",
                        "project_url": "https://gitlab.example.com/proj",
                        "file_name": "b.py",
                        "line_url": "https://gitlab.example.com/proj/-/blob/main/b.py#L2",
                        "data": "foo bar",
                    },
                ],
            )
            job = store.get_job("job-1")
            jobs = store.list_jobs_for_user("user-1")
            self.assertIsNotNone(job)
            self.assertEqual(job["result_count"], 2)
            self.assertEqual(jobs[0]["result_count"], 2)

    def test_store_can_page_job_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ServeStore(tmpdir)
            store.ensure_initialized()
            store.insert_job(
                {
                    "id": "job-2",
                    "owner_identity": "user-1",
                    "gitlab_url": "https://gitlab.example.com",
                    "project_ids": [],
                    "keywords": ["foo"],
                    "branch_mode": "all",
                    "branch_name": None,
                    "formats": ["xlsx"],
                    "status": "completed",
                    "progress": 100,
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "started_at": None,
                    "finished_at": None,
                    "failure_reason": None,
                    "export_base_name": None,
                    "export_paths": [],
                    "original_job_id": None,
                }
            )
            store.add_job_results(
                "job-2",
                [
                    {
                        "word": "foo",
                        "branch": "main",
                        "project_id": 1,
                        "project_name": "proj",
                        "project_url": "https://gitlab.example.com/proj",
                        "file_name": f"f{i}.py",
                        "line_url": f"https://gitlab.example.com/proj/-/blob/main/f{i}.py#L{i}",
                        "data": f"foo {i}",
                    }
                    for i in range(5)
                ],
            )
            rows, total_count = store.list_job_results_page("job-2", limit=2, offset=2)
            self.assertEqual(total_count, 5)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["file_name"], "f2.py")
            filtered_rows, filtered_total = store.list_job_results_page("job-2", query="foo 4", limit=10, offset=0)
            self.assertEqual(filtered_total, 1)
            self.assertEqual(filtered_rows[0]["file_name"], "f4.py")


class WebUiHtmlTests(unittest.TestCase):
    def test_build_app_html_contains_workbench_views(self) -> None:
        html = build_app_html()
        self.assertIn("GCS Workbench", html)
        self.assertIn("搜索", html)
        self.assertIn("执行日志流", html)
        self.assertIn("结果批次总览", html)
        self.assertIn("系统设置", html)
        self.assertIn("没有 Token？展开创建指引", html)
        self.assertIn("personal_access_tokens", html)
        self.assertIn("api", html)
        self.assertIn("read_api", html)


if __name__ == "__main__":
    unittest.main()
