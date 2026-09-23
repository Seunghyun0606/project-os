from pathlib import Path

import pytest

from projectctl.scaffold import install_scaffold
from projectctl.workflow import FileWorkflowRegistry


def test_workflow_registry_loads_steps(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    path = tmp_path / ".project-os/workflows/demo.yaml"
    path.write_text(
        """
id: demo
steps:
  - id: implement
    role: developer
    task:
      id: TASK-1
    context:
      spec: specs/feature/demo.md
  - id: review
    role: reviewer
    approval_gate: human-review
""".strip()
        + "\n",
        encoding="utf-8",
    )

    workflow = FileWorkflowRegistry(tmp_path).load("demo")

    assert workflow.id == "demo"
    assert [step.id for step in workflow.steps] == ["implement", "review"]
    assert workflow.steps[1].approval_gate == "human-review"


def test_workflow_registry_rejects_duplicate_step_ids(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    path = tmp_path / ".project-os/workflows/demo.yaml"
    path.write_text(
        """
id: demo
steps:
  - id: same
    role: developer
  - id: same
    role: reviewer
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate workflow step id"):
        FileWorkflowRegistry(tmp_path).load("demo")


def test_workflow_path_cannot_escape_project_root(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    outside = tmp_path.parent / "outside-workflow.yaml"
    outside.write_text("id: outside\nsteps:\n  - id: x\n    role: developer\n", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the project root"):
        FileWorkflowRegistry(tmp_path).load("../outside-workflow.yaml")
