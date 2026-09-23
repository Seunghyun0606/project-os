from pathlib import Path

from projectctl.central_store import CentralControlStore
from projectctl.control_service import CentralControlService
from projectctl.session_commands import SessionCommandHandler


def _control(tmp_path: Path) -> CentralControlService:
    store = CentralControlStore(tmp_path / "control.db")
    store.upsert_project({
        "project_id": "project-os",
        "project_name": "Project OS",
        "root_path": str(tmp_path / "project-os"),
        "project_status": "active",
        "current_milestone": None,
        "human_gate": False,
        "scaffold_version": "0.2.0",
        "schema_version": "1",
        "package_compatibility": ">=0.2,<1.0",
        "compatibility_status": "compatible",
        "compatibility_reason": "ok",
    })
    return CentralControlService(store)


def test_session_commands_support_status_new_and_list(tmp_path: Path):
    control = _control(tmp_path)
    handler = SessionCommandHandler(control)

    empty = handler.handle("/session", project_id="project-os")
    created = handler.handle(
        "/session new",
        project_id="project-os",
        worker_id="desktop-home",
    )
    current = handler.handle("/session", project_id="project-os")
    listed = handler.handle("/sessions", project_id="project-os")

    assert empty["payload"] is None
    assert created["payload"]["codex_session_id"] is None
    assert created["payload"]["status"] == "idle"
    assert created["payload"]["created_by"] == "telegram"
    assert current["payload"]["session_id"] == created["payload"]["session_id"]
    assert "Project: project-os" in current["message"]
    assert created["payload"]["session_id"] in listed["message"]


def test_non_session_text_is_not_claimed(tmp_path: Path):
    handler = SessionCommandHandler(_control(tmp_path))

    assert handler.handle("다음 작업 진행해줘", project_id="project-os") is None
