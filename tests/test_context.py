from pathlib import Path

import yaml

from projectctl.context import FileContextBuilder
from projectctl.project import Project
from projectctl.scaffold import install_scaffold


def _write_yaml(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_context_uses_only_declared_resources_and_dependency_summaries(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    (tmp_path / "specs/feature/needed.md").write_text("# Needed\nfeature context", encoding="utf-8")
    (tmp_path / "secret.md").write_text("must not be loaded", encoding="utf-8")

    _write_yaml(tmp_path / ".project-os/state/backlog.yaml", {
        "tasks": [
            {"id": "TASK-0", "status": "done", "role": "developer"},
            {
                "id": "TASK-1",
                "status": "ready",
                "role": "developer",
                "depends_on": ["TASK-0"],
                "specs": ["specs/feature/needed.md"],
                "active_decisions": [".project-os/decisions/ADR-001.yaml"],
            },
        ]
    })
    _write_yaml(tmp_path / ".project-os/decisions/ADR-001.yaml", {
        "id": "ADR-001",
        "status": "active",
        "applies_to": ["TASK-1"],
        "decision": "Use deterministic lookup",
    })
    _write_yaml(tmp_path / ".project-os/tasks/results/TASK-0.yaml", {
        "task": "TASK-0",
        "status": "submitted",
        "summary": "Dependency output",
        "artifacts": ["src/example.py"],
        "private_detail": "not copied into summary",
    })

    package = FileContextBuilder(Project(tmp_path)).build("TASK-1")
    paths = {item["path"] for item in package["resources"]}

    assert "specs/feature/needed.md" in paths
    assert ".project-os/decisions/ADR-001.yaml" in paths
    assert "secret.md" not in paths
    assert package["task_results"] == [{
        "task": "TASK-0",
        "status": "submitted",
        "summary": "Dependency output",
        "artifacts": ["src/example.py"],
    }]


def test_context_honors_role_token_budget(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    (tmp_path / "specs/feature/large.md").write_text("x" * 12000, encoding="utf-8")
    _write_yaml(tmp_path / ".project-os/state/backlog.yaml", {
        "tasks": [{
            "id": "TASK-1",
            "status": "ready",
            "role": "developer",
            "specs": ["specs/feature/large.md"],
        }]
    })
    _write_yaml(tmp_path / ".project-os/profile.yaml", {
        "profile": "default",
        "quality_profile": "standard",
        "inherit": {"roles": "default", "context": "default", "quality": "standard"},
        "overrides": {"context": {"developer": {"target_tokens": 1000}}},
    })

    package = FileContextBuilder(Project(tmp_path)).build("TASK-1")

    assert package["token_budget"] == 1000
    assert package["estimated_tokens"] <= 1000
    assert package["truncated"] is True
    assert len(package["resources"]) == 1
    assert len(package["resources"][0]["content"]) < 12000
