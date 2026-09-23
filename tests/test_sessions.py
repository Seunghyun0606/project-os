import sqlite3
from pathlib import Path

import pytest

from projectctl.central_store import CONTROL_DB_SCHEMA_VERSION, CentralControlStore
from projectctl.sessions import SessionLockedError, SessionService


def _register(store: CentralControlStore, tmp_path: Path, project_id: str) -> None:
    store.upsert_project({
        "project_id": project_id,
        "project_name": project_id,
        "root_path": str(tmp_path / project_id),
        "project_status": "active",
        "current_milestone": None,
        "human_gate": False,
        "scaffold_version": "0.2.0",
        "schema_version": "1",
        "package_compatibility": ">=0.2,<1.0",
        "compatibility_status": "compatible",
        "compatibility_reason": "ok",
    })


def test_v1_control_db_migrates_to_session_schema(tmp_path: Path):
    path = tmp_path / "control.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE projects (
            project_id TEXT PRIMARY KEY
        );
        PRAGMA user_version = 1;
        """
    )
    connection.commit()
    connection.close()

    store = CentralControlStore(path)

    assert store.db_schema_version() == CONTROL_DB_SCHEMA_VERSION == 2
    with store.connect() as migrated:
        tables = {
            row[0]
            for row in migrated.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {"sessions", "jobs"}.issubset(tables)


def test_first_job_creates_session_and_captures_codex_thread(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    service = SessionService(store)

    started = service.begin_job(
        "project-os",
        "JOB-001",
        source="telegram",
        worker_id="desktop-home",
        prompt_preview="현재 구현 상태 확인해줘",
    )

    assert started["job"]["execution_mode"] == "new_session"
    assert started["job"]["session_id"] == started["session"]["session_id"]
    assert started["session"]["status"] == "running"
    assert started["session"]["codex_session_id"] is None

    bound = service.bind_thread(
        "JOB-001",
        "019f1234-aaaa-bbbb-cccc-1234567890ab",
    )
    finished = service.finish_job("JOB-001")

    assert bound["matched"] is True
    assert finished["session"]["status"] == "idle"
    assert finished["session"]["codex_session_id"] == (
        "019f1234-aaaa-bbbb-cccc-1234567890ab"
    )
    assert finished["job"]["codex_session_id"] == (
        "019f1234-aaaa-bbbb-cccc-1234567890ab"
    )


def test_second_job_reuses_same_session_and_codex_id(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    service = SessionService(store)

    first = service.begin_job("project-os", "JOB-001")
    session_id = first["session"]["session_id"]
    codex_id = "019f1234-aaaa-bbbb-cccc-1234567890ab"
    service.bind_thread("JOB-001", codex_id)
    service.finish_job("JOB-001")

    second = service.begin_job(
        "project-os",
        "JOB-002",
        prompt_preview="다음 작업 진행해줘",
    )

    assert second["session"]["session_id"] == session_id
    assert second["job"]["execution_mode"] == "resumed_session"
    assert second["job"]["codex_session_id"] == codex_id
    assert len(service.list_sessions("project-os")) == 1
    assert len(service.list_jobs(session_id)) == 2


def test_explicit_new_session_rolls_over_without_deleting_history(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    service = SessionService(store)

    first = service.begin_job("project-os", "JOB-001")
    first_id = first["session"]["session_id"]
    service.bind_thread("JOB-001", "019f1234-aaaa-bbbb-cccc-1234567890ab")
    service.finish_job("JOB-001")

    second = service.new_session(
        "project-os",
        created_by="telegram",
        worker_id="desktop-home",
        title="Fresh context",
    )

    assert second["session_id"] != first_id
    assert second["codex_session_id"] is None
    assert second["status"] == "idle"
    sessions = service.list_sessions("project-os")
    assert {item["session_id"] for item in sessions} == {
        first_id,
        second["session_id"],
    }
    assert service.get_session(first_id)["status"] == "closed"


def test_project_switch_keeps_independent_active_sessions(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    _register(store, tmp_path, "dailytown")
    service = SessionService(store)

    one = service.begin_job("project-os", "JOB-P1")
    service.bind_thread("JOB-P1", "019f1111-aaaa-bbbb-cccc-1234567890ab")
    service.finish_job("JOB-P1")

    two = service.begin_job("dailytown", "JOB-D1")
    service.bind_thread("JOB-D1", "019f2222-aaaa-bbbb-cccc-1234567890ab")
    service.finish_job("JOB-D1")

    resumed = service.begin_job("project-os", "JOB-P2")

    assert resumed["session"]["session_id"] == one["session"]["session_id"]
    assert resumed["session"]["session_id"] != two["session"]["session_id"]
    assert resumed["job"]["execution_mode"] == "resumed_session"


def test_resume_thread_mismatch_marks_error_and_recovers_same_job(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    service = SessionService(store)

    first = service.begin_job("project-os", "JOB-001")
    old_session_id = first["session"]["session_id"]
    service.bind_thread("JOB-001", "019f1111-aaaa-bbbb-cccc-1234567890ab")
    service.finish_job("JOB-001")

    resumed = service.begin_job("project-os", "JOB-002")
    assert resumed["job"]["execution_mode"] == "resumed_session"

    mismatch = service.bind_thread(
        "JOB-002",
        "019f9999-aaaa-bbbb-cccc-1234567890ab",
    )

    assert mismatch["matched"] is False
    assert mismatch["error_code"] == "SESSION_NOT_FOUND"
    assert service.get_session(old_session_id)["status"] == "error"

    recovered = service.recover_job("JOB-002")

    assert recovered["session"]["session_id"] != old_session_id
    assert recovered["session"]["codex_session_id"] is None
    assert recovered["session"]["status"] == "running"
    assert recovered["job"]["execution_mode"] == "new_session"
    assert recovered["job"]["metadata"]["recovery_from_session_id"] == old_session_id


def test_concurrent_job_is_blocked_by_session_lock(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path, "project-os")
    service = SessionService(store)

    service.begin_job("project-os", "JOB-001")

    with pytest.raises(SessionLockedError, match="running under JOB-001"):
        service.begin_job("project-os", "JOB-002")


def test_restart_restores_existing_codex_session_from_sqlite(tmp_path: Path):
    path = tmp_path / "control.db"
    first_store = CentralControlStore(path)
    _register(first_store, tmp_path, "project-os")
    first_service = SessionService(first_store)

    started = first_service.begin_job("project-os", "JOB-001")
    session_id = started["session"]["session_id"]
    codex_id = "019f1234-aaaa-bbbb-cccc-1234567890ab"
    first_service.bind_thread("JOB-001", codex_id)
    first_service.finish_job("JOB-001")

    restarted_service = SessionService(CentralControlStore(path))
    next_job = restarted_service.begin_job("project-os", "JOB-002")

    assert next_job["session"]["session_id"] == session_id
    assert next_job["job"]["codex_session_id"] == codex_id
    assert next_job["job"]["execution_mode"] == "resumed_session"
