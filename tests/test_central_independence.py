from pathlib import Path

from projectctl.central_store import CentralControlStore
from projectctl.control_service import CentralControlService
from projectctl.project import Project
from projectctl.scaffold import install_scaffold


def test_consumer_project_remains_readable_after_central_db_is_deleted(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    install_scaffold(root, project_id="demo", project_name="Demo")
    db = tmp_path / "control.db"

    service = CentralControlService(CentralControlStore(db))
    service.register_project(root)
    assert db.exists()

    db.unlink()

    project = Project(root)
    status = project.status()

    assert status.project_id == "demo"
    assert status.project_name == "Demo"
    assert status.project_status == "active"
