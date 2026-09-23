from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from .central_store import CentralControlStore


SESSION_STATUSES = {"idle", "running", "closed", "error"}
SESSION_ERROR_CODES = {
    "SESSION_NOT_FOUND",
    "SESSION_LOCKED",
    "CODEX_START_FAILED",
    "CODEX_RESUME_FAILED",
    "SESSION_STALE_LOCK_RECOVERED",
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
_CODEX_SESSION_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


class SessionLockedError(RuntimeError):
    pass


class SessionStateError(RuntimeError):
    pass


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: str | None) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    payload = json.loads(value)
    return payload if isinstance(payload, dict) else {}


def _safe_id(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or not _SAFE_ID.fullmatch(normalized):
        raise ValueError(
            f"{label} must contain only letters, numbers, dot, underscore, colon or hyphen"
        )
    return normalized


def validate_codex_session_id(value: str) -> str:
    normalized = value.strip()
    if not _CODEX_SESSION_ID.fullmatch(normalized):
        raise ValueError("Invalid Codex session id")
    return normalized


def new_session_id() -> str:
    return f"S-{_now_dt():%Y%m%d}-{uuid4().hex[:8].upper()}"


def new_job_id(prefix: str = "JOB") -> str:
    return f"{prefix}-{_now_dt():%Y%m%d-%H%M%S}-{uuid4().hex[:6].upper()}"


class SessionService:
    """Owns Project OS project-session/job operational state in the control DB."""

    def __init__(self, store: CentralControlStore, stale_lock_seconds: int = 7200):
        if stale_lock_seconds <= 0:
            raise ValueError("stale_lock_seconds must be positive")
        self.store = store
        self.stale_lock_seconds = stale_lock_seconds

    @staticmethod
    def _session(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = _decode(item.pop("metadata_json", None))
        return item

    @staticmethod
    def _job(row: Any) -> dict[str, Any]:
        item = dict(row)
        item["metadata"] = _decode(item.pop("metadata_json", None))
        return item

    @staticmethod
    def _require_project(connection, project_id: str) -> None:
        if connection.execute(
            "SELECT 1 FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchone() is None:
            raise KeyError(f"Unknown registered project: {project_id}")

    def _is_stale(self, locked_at: str | None) -> bool:
        if not locked_at:
            return True
        try:
            locked = datetime.fromisoformat(locked_at)
        except ValueError:
            return True
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return _now_dt() - locked > timedelta(seconds=self.stale_lock_seconds)

    def _recover_stale_lock(self, connection, row: Any) -> bool:
        if str(row["status"]) != "running" or not self._is_stale(row["locked_at"]):
            return False

        now = _now()
        locked_job = row["locked_by_job_id"]
        if locked_job:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    error_code = 'SESSION_STALE_LOCK_RECOVERED',
                    completed_at = ?
                WHERE job_id = ? AND status = 'running'
                """,
                (now, locked_job),
            )
        connection.execute(
            """
            UPDATE sessions
            SET status = 'idle',
                locked_by_job_id = NULL,
                locked_at = NULL,
                last_activity_at = ?
            WHERE session_id = ?
            """,
            (now, row["session_id"]),
        )
        return True

    def _insert_session(
        self,
        connection,
        project_id: str,
        *,
        created_by: str,
        worker_id: str | None,
        title: str | None,
        metadata: dict[str, Any] | None,
    ) -> str:
        session_id = new_session_id()
        now = _now()
        connection.execute(
            """
            INSERT INTO sessions (
                session_id, project_id, codex_session_id, status,
                created_at, last_activity_at, created_by, worker_id,
                last_job_id, title, metadata_json, locked_by_job_id,
                locked_at, closed_at
            ) VALUES (?, ?, NULL, 'idle', ?, ?, ?, ?, NULL, ?, ?, NULL, NULL, NULL)
            """,
            (
                session_id,
                project_id,
                now,
                now,
                created_by,
                worker_id,
                title,
                _json(metadata or {"codex_source": "exec"}),
            ),
        )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any]:
        safe = _safe_id(session_id, "session_id")
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (safe,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown session: {safe}")
        return self._session(row)

    def active_session(self, project_id: str) -> dict[str, Any] | None:
        with self.store.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM sessions
                WHERE project_id = ? AND status IN ('idle', 'running')
                ORDER BY last_activity_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            if row is not None and self._recover_stale_lock(connection, row):
                row = connection.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (row["session_id"],),
                ).fetchone()
        return None if row is None else self._session(row)

    def list_sessions(
        self,
        project_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        clauses = []
        args: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            args.append(project_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        args.append(limit)
        with self.store.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM sessions"
                + where
                + " ORDER BY last_activity_at DESC, session_id DESC LIMIT ?",
                tuple(args),
            ).fetchall()
        return [self._session(row) for row in rows]

    def new_session(
        self,
        project_id: str,
        *,
        created_by: str = "manual",
        worker_id: str | None = None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project_id = _safe_id(project_id, "project_id")
        with self.store.connect() as connection:
            self._require_project(connection, project_id)
            active = connection.execute(
                """
                SELECT * FROM sessions
                WHERE project_id = ? AND status IN ('idle', 'running')
                ORDER BY last_activity_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            if active is not None and str(active["status"]) == "running":
                if self._recover_stale_lock(connection, active):
                    active = connection.execute(
                        "SELECT * FROM sessions WHERE session_id = ?",
                        (active["session_id"],),
                    ).fetchone()
                if active is not None and str(active["status"]) == "running":
                    raise SessionLockedError(
                        f"Session {active['session_id']} is running under "
                        f"{active['locked_by_job_id']}"
                    )
            now = _now()
            connection.execute(
                """
                UPDATE sessions
                SET status = 'closed',
                    closed_at = ?,
                    last_activity_at = ?,
                    locked_by_job_id = NULL,
                    locked_at = NULL
                WHERE project_id = ? AND status = 'idle'
                """,
                (now, now, project_id),
            )
            session_id = self._insert_session(
                connection,
                project_id,
                created_by=created_by,
                worker_id=worker_id,
                title=title,
                metadata=metadata,
            )
            row = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return self._session(row)

    def begin_job(
        self,
        project_id: str,
        job_id: str,
        *,
        source: str = "telegram",
        worker_id: str | None = None,
        prompt_preview: str | None = None,
    ) -> dict[str, Any]:
        project_id = _safe_id(project_id, "project_id")
        job_id = _safe_id(job_id, "job_id")
        with self.store.connect() as connection:
            self._require_project(connection, project_id)
            if connection.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone() is not None:
                raise ValueError(f"Job already exists: {job_id}")

            row = connection.execute(
                """
                SELECT * FROM sessions
                WHERE project_id = ? AND status IN ('idle', 'running')
                ORDER BY last_activity_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            if row is None:
                session_id = self._insert_session(
                    connection,
                    project_id,
                    created_by=source,
                    worker_id=worker_id,
                    title=None,
                    metadata=None,
                )
                row = connection.execute(
                    "SELECT * FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
            elif str(row["status"]) == "running":
                if self._recover_stale_lock(connection, row):
                    row = connection.execute(
                        "SELECT * FROM sessions WHERE session_id = ?",
                        (row["session_id"],),
                    ).fetchone()
                if row is not None and str(row["status"]) == "running":
                    raise SessionLockedError(
                        f"Session {row['session_id']} is running under "
                        f"{row['locked_by_job_id']}"
                    )

            codex_session_id = row["codex_session_id"]
            execution_mode = "resumed_session" if codex_session_id else "new_session"
            now = _now()
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, project_id, session_id, codex_session_id,
                    source, worker_id, execution_mode, status,
                    prompt_preview, error_code, metadata_json,
                    created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?, NULL, '{}', ?, ?, NULL)
                """,
                (
                    job_id,
                    project_id,
                    row["session_id"],
                    codex_session_id,
                    source,
                    worker_id,
                    execution_mode,
                    (prompt_preview or "")[:240] or None,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE sessions
                SET status = 'running',
                    worker_id = COALESCE(?, worker_id),
                    last_job_id = ?,
                    last_activity_at = ?,
                    locked_by_job_id = ?,
                    locked_at = ?
                WHERE session_id = ?
                """,
                (
                    worker_id,
                    job_id,
                    now,
                    job_id,
                    now,
                    row["session_id"],
                ),
            )
            session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (row["session_id"],),
            ).fetchone()
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return {"session": self._session(session), "job": self._job(job)}

    def begin_attach(
        self,
        session_id: str,
        *,
        job_id: str | None = None,
        worker_id: str = "desktop",
    ) -> dict[str, Any]:
        session_id = _safe_id(session_id, "session_id")
        job_id = _safe_id(job_id or new_job_id("ATTACH"), "job_id")
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown session: {session_id}")
            if not row["codex_session_id"]:
                raise SessionStateError(
                    f"Session {session_id} has no Codex session yet; run a job first"
                )
            if str(row["status"]) == "running":
                if self._recover_stale_lock(connection, row):
                    row = connection.execute(
                        "SELECT * FROM sessions WHERE session_id = ?",
                        (session_id,),
                    ).fetchone()
                if str(row["status"]) == "running":
                    raise SessionLockedError(
                        f"Session {session_id} is running under {row['locked_by_job_id']}"
                    )
            if str(row["status"]) != "idle":
                raise SessionStateError(
                    f"Session {session_id} is not attachable from status {row['status']}"
                )

            now = _now()
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, project_id, session_id, codex_session_id,
                    source, worker_id, execution_mode, status,
                    prompt_preview, error_code, metadata_json,
                    created_at, started_at, completed_at
                ) VALUES (?, ?, ?, ?, 'desktop', ?, 'attached_session', 'running',
                          NULL, NULL, '{}', ?, ?, NULL)
                """,
                (
                    job_id,
                    row["project_id"],
                    session_id,
                    row["codex_session_id"],
                    worker_id,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                UPDATE sessions
                SET status = 'running',
                    worker_id = ?,
                    last_job_id = ?,
                    last_activity_at = ?,
                    locked_by_job_id = ?,
                    locked_at = ?
                WHERE session_id = ?
                """,
                (worker_id, job_id, now, job_id, now, session_id),
            )
            session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return {"session": self._session(session), "job": self._job(job)}

    def bind_thread(self, job_id: str, thread_id: str) -> dict[str, Any]:
        job_id = _safe_id(job_id, "job_id")
        thread_id = validate_codex_session_id(thread_id)
        with self.store.connect() as connection:
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if job is None:
                raise KeyError(f"Unknown job: {job_id}")
            session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (job["session_id"],),
            ).fetchone()
            if session is None:
                raise KeyError(f"Unknown session: {job['session_id']}")
            if job["status"] != "running" or session["locked_by_job_id"] != job_id:
                raise SessionStateError(f"Job {job_id} does not own the session lock")

            expected = session["codex_session_id"]
            now = _now()
            if expected and str(expected) != thread_id:
                metadata = _decode(job["metadata_json"])
                metadata["resume_mismatch"] = {
                    "expected": expected,
                    "actual": thread_id,
                }
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = 'failed',
                        error_code = 'SESSION_NOT_FOUND',
                        metadata_json = ?,
                        completed_at = ?
                    WHERE job_id = ?
                    """,
                    (_json(metadata), now, job_id),
                )
                connection.execute(
                    """
                    UPDATE sessions
                    SET status = 'error',
                        last_activity_at = ?,
                        locked_by_job_id = NULL,
                        locked_at = NULL
                    WHERE session_id = ?
                    """,
                    (now, session["session_id"]),
                )
                return {
                    "matched": False,
                    "error_code": "SESSION_NOT_FOUND",
                    "expected_codex_session_id": expected,
                    "actual_codex_session_id": thread_id,
                    "session_id": session["session_id"],
                    "job_id": job_id,
                }

            connection.execute(
                """
                UPDATE sessions
                SET codex_session_id = ?,
                    last_activity_at = ?
                WHERE session_id = ?
                """,
                (thread_id, now, session["session_id"]),
            )
            connection.execute(
                """
                UPDATE jobs
                SET codex_session_id = ?
                WHERE job_id = ?
                """,
                (thread_id, job_id),
            )
            return {
                "matched": True,
                "error_code": None,
                "codex_session_id": thread_id,
                "session_id": session["session_id"],
                "job_id": job_id,
            }

    def recover_job(
        self,
        job_id: str,
        *,
        created_by: str | None = None,
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        job_id = _safe_id(job_id, "job_id")
        with self.store.connect() as connection:
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if job is None:
                raise KeyError(f"Unknown job: {job_id}")
            if job["status"] != "failed":
                raise SessionStateError(f"Job {job_id} is not failed")
            if job["error_code"] not in {"SESSION_NOT_FOUND", "CODEX_RESUME_FAILED"}:
                raise SessionStateError(
                    f"Job {job_id} is not recoverable from {job['error_code']}"
                )

            old_session_id = str(job["session_id"])
            active = connection.execute(
                """
                SELECT * FROM sessions
                WHERE project_id = ? AND status IN ('idle', 'running')
                LIMIT 1
                """,
                (job["project_id"],),
            ).fetchone()
            if active is not None:
                raise SessionStateError(
                    f"Project {job['project_id']} already has active session "
                    f"{active['session_id']}"
                )

            session_id = self._insert_session(
                connection,
                str(job["project_id"]),
                created_by=created_by or str(job["source"]),
                worker_id=worker_id or job["worker_id"],
                title=None,
                metadata={
                    "codex_source": "exec",
                    "recovery_from_session_id": old_session_id,
                },
            )
            now = _now()
            metadata = _decode(job["metadata_json"])
            metadata["recovery_from_session_id"] = old_session_id
            connection.execute(
                """
                UPDATE jobs
                SET session_id = ?,
                    codex_session_id = NULL,
                    execution_mode = 'new_session',
                    status = 'running',
                    worker_id = COALESCE(?, worker_id),
                    error_code = NULL,
                    metadata_json = ?,
                    started_at = ?,
                    completed_at = NULL
                WHERE job_id = ?
                """,
                (
                    session_id,
                    worker_id,
                    _json(metadata),
                    now,
                    job_id,
                ),
            )
            connection.execute(
                """
                UPDATE sessions
                SET status = 'running',
                    last_job_id = ?,
                    worker_id = COALESCE(?, worker_id),
                    last_activity_at = ?,
                    locked_by_job_id = ?,
                    locked_at = ?
                WHERE session_id = ?
                """,
                (job_id, worker_id, now, job_id, now, session_id),
            )
            session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            refreshed_job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return {"session": self._session(session), "job": self._job(refreshed_job)}

    def finish_job(
        self,
        job_id: str,
        *,
        success: bool = True,
        error_code: str | None = None,
        session_fatal: bool = False,
    ) -> dict[str, Any]:
        job_id = _safe_id(job_id, "job_id")
        if error_code and error_code not in SESSION_ERROR_CODES:
            raise ValueError(f"Unsupported session error code: {error_code}")
        with self.store.connect() as connection:
            job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if job is None:
                raise KeyError(f"Unknown job: {job_id}")
            session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (job["session_id"],),
            ).fetchone()
            if session is None:
                raise KeyError(f"Unknown session: {job['session_id']}")
            if job["status"] != "running":
                raise SessionStateError(
                    f"Job {job_id} is already terminal: {job['status']}"
                )
            if session["locked_by_job_id"] != job_id:
                raise SessionStateError(f"Job {job_id} does not own the session lock")

            now = _now()
            job_status = "completed" if success else "failed"
            next_session_status = "error" if session_fatal else "idle"
            connection.execute(
                """
                UPDATE jobs
                SET status = ?,
                    error_code = ?,
                    codex_session_id = COALESCE(codex_session_id, ?),
                    completed_at = ?
                WHERE job_id = ?
                """,
                (
                    job_status,
                    error_code,
                    session["codex_session_id"],
                    now,
                    job_id,
                ),
            )
            connection.execute(
                """
                UPDATE sessions
                SET status = ?,
                    last_activity_at = ?,
                    locked_by_job_id = NULL,
                    locked_at = NULL
                WHERE session_id = ?
                """,
                (next_session_status, now, session["session_id"]),
            )
            refreshed_job = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            refreshed_session = connection.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session["session_id"],),
            ).fetchone()
        return {
            "session": self._session(refreshed_session),
            "job": self._job(refreshed_job),
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        job_id = _safe_id(job_id, "job_id")
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown job: {job_id}")
        return self._job(row)

    def list_jobs(self, session_id: str) -> list[dict[str, Any]]:
        session_id = _safe_id(session_id, "session_id")
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM jobs
                WHERE session_id = ?
                ORDER BY created_at, job_id
                """,
                (session_id,),
            ).fetchall()
        return [self._job(row) for row in rows]
