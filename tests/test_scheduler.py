from pathlib import Path

import yaml

from projectctl.project import Project
from projectctl.scheduler import DeterministicTaskScheduler


def write_project(tmp_path: Path, tasks):
    os_root = tmp_path / ".project-os"
    (os_root / "state").mkdir(parents=True)
    (os_root / "manifest.yaml").write_text(
        yaml.safe_dump({
            "project_os": {"scaffold_version": "0.1.0", "schema_version": "1"},
            "project": {"id": "x", "name": "X"},
            "profile": "default",
            "sources": {},
        }),
        encoding="utf-8",
    )
    (os_root / "state" / "current.yaml").write_text(
        yaml.safe_dump({"project_status": "active"}), encoding="utf-8"
    )
    (os_root / "state" / "backlog.yaml").write_text(
        yaml.safe_dump({"tasks": tasks}), encoding="utf-8"
    )
    return Project(tmp_path)


def test_next_task_respects_priority_and_dependencies(tmp_path):
    project = write_project(tmp_path, [
        {"id": "TASK-1", "role": "developer", "priority": "P0", "status": "done"},
        {"id": "TASK-2", "role": "developer", "priority": "P1", "status": "ready", "depends_on": ["TASK-1"]},
        {"id": "TASK-3", "role": "developer", "priority": "P0", "status": "ready", "depends_on": ["TASK-X"]},
    ])
    task = DeterministicTaskScheduler(project).next_task("developer")
    assert task["id"] == "TASK-2"


def test_next_task_skips_human_gate(tmp_path):
    project = write_project(tmp_path, [
        {"id": "TASK-1", "role": "developer", "priority": "P0", "status": "ready", "human_gate": True},
        {"id": "TASK-2", "role": "developer", "priority": "P1", "status": "ready"},
    ])
    task = DeterministicTaskScheduler(project).next_task("developer")
    assert task["id"] == "TASK-2"


def test_next_task_filters_role(tmp_path):
    project = write_project(tmp_path, [
        {"id": "TASK-1", "role": "reviewer", "priority": "P0", "status": "ready"},
        {"id": "TASK-2", "role": "developer", "priority": "P1", "status": "ready"},
    ])
    assert DeterministicTaskScheduler(project).next_task("developer")["id"] == "TASK-2"
