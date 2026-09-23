import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import projectctl.cli as cli_module
from projectctl.cli import app
from projectctl.control_service import CentralControlService
from projectctl.central_store import CentralControlStore
from projectctl.scaffold import install_scaffold


runner = CliRunner()
CODEX_ID = "019f1234-aaaa-bbbb-cccc-1234567890ab"


def _registered(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    root.mkdir()
    install_scaffold(root, project_id="project-os", project_name="Project OS")
    db = tmp_path / "control.db"
    result = runner.invoke(
        app,
        ["control", "register", str(root), "--db", str(db)],
    )
    assert result.exit_code == 0, result.output
    return root, db


def test_sessions_cli_lists_and_shows_active_session(tmp_path: Path):
    _, db = _registered(tmp_path)

    created = runner.invoke(
        app,
        [
            "session",
            "new",
            "project-os",
            "--created-by",
            "telegram",
            "--worker-id",
            "desktop-home",
            "--db",
            str(db),
            "--json",
        ],
    )
    listed = runner.invoke(
        app,
        ["sessions", "--project", "project-os", "--db", str(db), "--json"],
    )

    assert created.exit_code == 0, created.output
    assert listed.exit_code == 0, listed.output
    created_payload = json.loads(created.output)
    listed_payload = json.loads(listed.output)

    assert created_payload["project_id"] == "project-os"
    assert created_payload["codex_session_id"] is None
    assert listed_payload["sessions"][0]["session_id"] == created_payload["session_id"]


def test_remote_integration_cli_reuses_session(tmp_path: Path):
    _, db = _registered(tmp_path)

    first = runner.invoke(
        app,
        [
            "session",
            "begin-job",
            "project-os",
            "JOB-001",
            "--source",
            "telegram",
            "--worker-id",
            "desktop-home",
            "--db",
            str(db),
        ],
    )
    assert first.exit_code == 0, first.output
    first_payload = json.loads(first.output)
    assert first_payload["job"]["execution_mode"] == "new_session"

    bound = runner.invoke(
        app,
        ["session", "bind-thread", "JOB-001", CODEX_ID, "--db", str(db)],
    )
    done = runner.invoke(
        app,
        ["session", "finish-job", "JOB-001", "--db", str(db)],
    )
    second = runner.invoke(
        app,
        [
            "session",
            "begin-job",
            "project-os",
            "JOB-002",
            "--source",
            "telegram",
            "--db",
            str(db),
        ],
    )

    assert bound.exit_code == 0, bound.output
    assert done.exit_code == 0, done.output
    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["job"]["execution_mode"] == "resumed_session"
    assert second_payload["job"]["codex_session_id"] == CODEX_ID
    assert (
        second_payload["session"]["session_id"]
        == first_payload["session"]["session_id"]
    )


def test_session_attach_uses_codex_resume_and_releases_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root, db = _registered(tmp_path)
    service = CentralControlService(CentralControlStore(db))
    started = service.begin_session_job("project-os", "JOB-001")
    session_id = started["session"]["session_id"]
    service.bind_session_thread("JOB-001", CODEX_ID)
    service.finish_session_job("JOB-001")

    observed = {}

    def fake_attach(codex_session_id, **kwargs):
        observed["codex_session_id"] = codex_session_id
        observed["cwd"] = kwargs["cwd"]
        return 0

    monkeypatch.setattr(cli_module, "run_attach", fake_attach)

    attached = runner.invoke(
        app,
        ["session", "attach", session_id, "--db", str(db)],
    )

    assert attached.exit_code == 0, attached.output
    assert observed["codex_session_id"] == CODEX_ID
    assert observed["cwd"] == root.resolve()
    assert service.session(session_id)["status"] == "idle"
    jobs = SessionService(CentralControlStore(db)).list_jobs(session_id)
    assert jobs[-1]["execution_mode"] == "attached_session"
    assert jobs[-1]["status"] == "completed"


from projectctl.sessions import SessionService
