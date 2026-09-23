from pathlib import Path

import yaml

from projectctl.doctor import inspect
from projectctl.project import Project


def make_minimal(tmp_path: Path, tasks):
    (tmp_path / ".project-os/state").mkdir(parents=True)
    (tmp_path / ".project-os/manifest.yaml").write_text(
        yaml.safe_dump({
            "project_os": {"scaffold_version": "0.1.0", "schema_version": "1"},
            "project": {"id": "x", "name": "X"},
            "profile": "default",
            "sources": {},
        }), encoding="utf-8"
    )
    (tmp_path / ".project-os/state/current.yaml").write_text("project_status: active\n", encoding="utf-8")
    (tmp_path / ".project-os/state/roadmap.yaml").write_text("milestones: []\n", encoding="utf-8")
    (tmp_path / ".project-os/state/backlog.yaml").write_text(yaml.safe_dump({"tasks": tasks}), encoding="utf-8")
    (tmp_path / ".project-os/profile.yaml").write_text("profile: default\n", encoding="utf-8")
    (tmp_path / ".project-os/quality").mkdir(parents=True)
    (tmp_path / ".project-os/quality/gates.yaml").write_text("required: {}\n", encoding="utf-8")
    (tmp_path / ".project-os/context").mkdir(parents=True)
    (tmp_path / ".project-os/context/index.yaml").write_text("domains: {}\n", encoding="utf-8")
    (tmp_path / "PROJECT.md").write_text("# X\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    return Project(tmp_path)


def test_doctor_detects_missing_dependency(tmp_path):
    project = make_minimal(tmp_path, [
        {"id": "TASK-1", "status": "ready", "depends_on": ["TASK-NOPE"]}
    ])
    findings = inspect(project)
    assert any("missing task" in item.message for item in findings)


def test_doctor_detects_cycle(tmp_path):
    project = make_minimal(tmp_path, [
        {"id": "TASK-1", "status": "ready", "depends_on": ["TASK-2"]},
        {"id": "TASK-2", "status": "ready", "depends_on": ["TASK-1"]},
    ])
    findings = inspect(project)
    assert any("cycle" in item.message for item in findings)


def test_doctor_detects_duplicate_ids(tmp_path):
    project = make_minimal(tmp_path, [
        {"id": "TASK-1", "status": "ready"},
        {"id": "TASK-1", "status": "blocked"},
    ])
    findings = inspect(project)
    assert any("Duplicate task id" in item.message for item in findings)
