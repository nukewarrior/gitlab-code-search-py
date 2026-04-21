from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOCAL_CREDENTIAL_BACKEND = "local_v1"


def utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    session_id: str
    owner_identity: str
    is_active: bool


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class ServeStore:
    def __init__(self, workdir: str | Path) -> None:
        self.workdir = Path(workdir)
        self.exports_dir = self.workdir / "exports"
        self.db_path = self.workdir / "gcs.sqlite3"

    def ensure_initialized(self) -> None:
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    identity TEXT PRIMARY KEY,
                    gitlab_url TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    credential_key TEXT NOT NULL,
                    last_login_at TEXT,
                    last_active_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    owner_identity TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    owner_identity TEXT NOT NULL,
                    gitlab_url TEXT NOT NULL,
                    project_ids_json TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    branch_mode TEXT NOT NULL,
                    branch_name TEXT,
                    formats_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    export_base_name TEXT,
                    export_paths_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    failure_reason TEXT,
                    original_job_id TEXT
                );

                CREATE TABLE IF NOT EXISTS job_results (
                    job_id TEXT NOT NULL,
                    row_index INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    project_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    project_url TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    line_url TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY(job_id, row_index)
                );

                CREATE TABLE IF NOT EXISTS credentials (
                    credential_key TEXT PRIMARY KEY,
                    secret TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    user_identity TEXT,
                    session_id TEXT,
                    action TEXT NOT NULL,
                    target_type TEXT,
                    target_id TEXT,
                    summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    remote_addr TEXT,
                    user_agent TEXT
                );
                """
            )
            existing_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if "branch_name" not in existing_columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN branch_name TEXT")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, factory=ClosingConnection)
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_local_credential_backend(self) -> tuple[bool, str | None, int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?",
                ("credential_backend",),
            ).fetchone()
            current_backend = None if row is None else str(row["value"])
            if current_backend == LOCAL_CREDENTIAL_BACKEND:
                return False, current_backend, 0
            invalidated_sessions = conn.execute(
                "UPDATE sessions SET is_active = 0 WHERE is_active != 0"
            ).rowcount
            conn.execute(
                """
                INSERT INTO app_settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("credential_backend", LOCAL_CREDENTIAL_BACKEND),
            )
        return True, current_backend, invalidated_sessions

    def get_setting(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def upsert_user(
        self,
        identity: str,
        gitlab_url: str,
        display_name: str,
        is_admin: bool,
        credential_key: str,
    ) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users(identity, gitlab_url, display_name, is_admin, credential_key, last_login_at, last_active_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity) DO UPDATE SET
                    gitlab_url = excluded.gitlab_url,
                    display_name = excluded.display_name,
                    is_admin = excluded.is_admin,
                    credential_key = excluded.credential_key,
                    last_login_at = excluded.last_login_at,
                    last_active_at = excluded.last_active_at
                """,
                (identity, gitlab_url, display_name, int(is_admin), credential_key, now, now),
            )

    def upsert_credential(self, credential_key: str, secret: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO credentials(credential_key, secret, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(credential_key) DO UPDATE SET
                    secret = excluded.secret,
                    updated_at = excluded.updated_at
                """,
                (credential_key, secret, now),
            )

    def get_credential(self, credential_key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT secret FROM credentials WHERE credential_key = ?",
                (credential_key,),
            ).fetchone()
        return None if row is None else str(row["secret"])

    def delete_credential(self, credential_key: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM credentials WHERE credential_key = ?",
                (credential_key,),
            )

    def get_user(self, identity: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM users WHERE identity = ?", (identity,)).fetchone()

    def create_session(self, session_id: str, owner_identity: str) -> None:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, owner_identity, created_at, last_seen_at, is_active)
                VALUES(?, ?, ?, ?, 1)
                """,
                (session_id, owner_identity, now, now),
            )

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return SessionRecord(
            session_id=str(row["session_id"]),
            owner_identity=str(row["owner_identity"]),
            is_active=bool(row["is_active"]),
        )

    def touch_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET last_seen_at = ? WHERE session_id = ?", (utc_now(), session_id))

    def deactivate_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))

    def insert_job(self, record: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs(
                    id, owner_identity, gitlab_url, project_ids_json, keywords_json, branch_mode, branch_name, formats_json,
                    status, progress, export_base_name, export_paths_json, created_at, started_at, finished_at,
                    failure_reason, original_job_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["owner_identity"],
                    record["gitlab_url"],
                    json.dumps(record["project_ids"]),
                    json.dumps(record["keywords"]),
                    record["branch_mode"],
                    record.get("branch_name"),
                    json.dumps(record["formats"]),
                    record["status"],
                    record.get("progress", 0),
                    record.get("export_base_name"),
                    json.dumps(record.get("export_paths", [])),
                    record["created_at"],
                    record.get("started_at"),
                    record.get("finished_at"),
                    record.get("failure_reason"),
                    record.get("original_job_id"),
                ),
            )

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        assignments = []
        values: list[Any] = []
        for key, value in fields.items():
            if key in {"project_ids", "keywords", "formats", "export_paths"}:
                key = f"{key}_json"
                value = json.dumps(value)
            assignments.append(f"{key} = ?")
            values.append(value)
        values.append(job_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", values)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT jobs.*, (
                    SELECT COUNT(*)
                    FROM job_results
                    WHERE job_results.job_id = jobs.id
                ) AS result_count
                FROM jobs
                WHERE id = ?
                """,
                (job_id,),
            ).fetchone()
        return None if row is None else self._decode_job_row(row)

    def list_jobs_for_user(self, owner_identity: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT jobs.*, (
                    SELECT COUNT(*)
                    FROM job_results
                    WHERE job_results.job_id = jobs.id
                ) AS result_count
                FROM jobs
                WHERE owner_identity = ?
                ORDER BY created_at DESC
                """,
                (owner_identity,),
            ).fetchall()
        return [self._decode_job_row(row) for row in rows]

    def add_job_results(self, job_id: str, rows: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO job_results(
                    job_id, row_index, word, branch, project_id, project_name, project_url, file_name, line_url, data
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        job_id,
                        index,
                        row["word"],
                        row["branch"],
                        row["project_id"],
                        row["project_name"],
                        row["project_url"],
                        row["file_name"],
                        row["line_url"],
                        row["data"],
                    )
                    for index, row in enumerate(rows)
                ],
            )

    def list_job_results(self, job_id: str, query: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM job_results WHERE job_id = ?"
        params: list[Any] = [job_id]
        if query:
            like = f"%{query}%"
            sql += (
                " AND (word LIKE ? OR branch LIKE ? OR project_name LIKE ? OR file_name LIKE ? OR data LIKE ? OR line_url LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])
        sql += " ORDER BY row_index"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def list_job_results_page(
        self,
        job_id: str,
        query: str | None = None,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        where_sql = "job_id = ?"
        params: list[Any] = [job_id]
        if query:
            like = f"%{query}%"
            where_sql += (
                " AND (word LIKE ? OR branch LIKE ? OR project_name LIKE ? OR file_name LIKE ? OR data LIKE ? OR line_url LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])
        count_sql = f"SELECT COUNT(*) FROM job_results WHERE {where_sql}"
        rows_sql = f"SELECT * FROM job_results WHERE {where_sql} ORDER BY row_index LIMIT ? OFFSET ?"
        with self._connect() as conn:
            total_count = int(conn.execute(count_sql, params).fetchone()[0])
            rows = conn.execute(rows_sql, [*params, limit, offset]).fetchall()
        return [dict(row) for row in rows], total_count

    def mark_unfinished_jobs_interrupted(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'interrupted',
                    finished_at = ?,
                    failure_reason = COALESCE(failure_reason, 'service restarted')
                WHERE status IN ('queued', 'running')
                """,
                (utc_now(),),
            )

    def add_audit_log(
        self,
        *,
        user_identity: str | None,
        session_id: str | None,
        action: str,
        target_type: str | None,
        target_id: str | None,
        summary: str,
        status: str,
        remote_addr: str | None,
        user_agent: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs(
                    created_at, user_identity, session_id, action, target_type, target_id, summary, status, remote_addr, user_agent
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (utc_now(), user_identity, session_id, action, target_type, target_id, summary, status, remote_addr, user_agent),
            )

    def list_audit_logs(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _decode_job_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "owner_identity": str(row["owner_identity"]),
            "gitlab_url": str(row["gitlab_url"]),
            "project_ids": json.loads(row["project_ids_json"]),
            "keywords": json.loads(row["keywords_json"]),
            "branch_mode": str(row["branch_mode"]),
            "branch_name": row["branch_name"],
            "formats": json.loads(row["formats_json"]),
            "status": str(row["status"]),
            "progress": int(row["progress"]),
            "export_base_name": row["export_base_name"],
            "export_paths": json.loads(row["export_paths_json"]),
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "failure_reason": row["failure_reason"],
            "original_job_id": row["original_job_id"],
            "result_count": int(row["result_count"]) if "result_count" in row.keys() else 0,
        }
