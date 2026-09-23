from pathlib import Path

import pytest
import yaml

from projectctl.handoffs import EvaluationService, HandoffStore
from projectctl.project import Project
from projectctl.scaffold import install_scaffold
from projectctl.transitions import CanonicalStateWriter


def _write_task(tmp_path: Path, status: str = "ready") -> Project:
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    backlog_path = tmp_path / ".project-os/state/backlog.yaml"
    backlog_path.write_text(
        yaml.safe_dump({
            "tasks": [{
                "id": "TASK-1",
                "title": "Implement",
                "role": "developer",
                "priority": "P0",
                "status": status,
                "acceptance": ["feature works"],
            }]
        }, sort_keys=False),
        encoding="utf-8",
    )
    return Project(tmp_path)


def test_reviewer_cannot_approve_own_implementation(tmp_path: Path):
    project = _write_task(tmp_path, status="active")
    handoffs = HandoffStore(project)
    handoffs.submit(
        "TASK-1",
        "implementation",
        {"status": "pass", "summary": "done", "evidence": ["pytest"]},
        role="developer",
        actor="agent-1",
    )

    with pytest.raises(PermissionError):
        handoffs.submit(
            "TASK-1",
            "review",
            {"status": "pass", "summary": "looks good"},
            role="reviewer",
            actor="agent-1",
        )


def test_permission_boundary_blocks_wrong_role(tmp_path: Path):
    project = _write_task(tmp_path, status="active")
    with pytest.raises(PermissionError):
        HandoffStore(project).submit(
            "TASK-1",
            "review",
            {"status": "pass"},
            role="developer",
            actor="developer-1",
        )


def test_pass_requires_configured_review_and_updates_state(tmp_path: Path):
    project = _write_task(tmp_path)
    CanonicalStateWriter(project).claim("TASK-1", "developer")
    handoffs = HandoffStore(project)
    handoffs.submit(
        "TASK-1",
        "implementation",
        {
            "status": "pass",
            "summary": "done",
            "evidence": ["pytest passed"],
            "verification": {"acceptance": "pass"},
        },
        role="developer",
        actor="developer-1",
    )

    with pytest.raises(ValueError, match="independent_review"):
        EvaluationService(project).evaluate(
            "TASK-1",
            {"decision": "PASS", "summary": "complete"},
            actor="evaluator-1",
        )

    handoffs.submit(
        "TASK-1",
        "review",
        {"status": "pass", "summary": "review passed", "critical_issues": 0},
        role="reviewer",
        actor="reviewer-1",
    )

    EvaluationService(project).evaluate(
        "TASK-1",
        {"decision": "PASS", "summary": "all gates passed"},
        actor="evaluator-1",
    )

    backlog = project.backlog()
    state = project.current_state()
    assert backlog["tasks"][0]["status"] == "done"
    assert "TASK-1" not in state.get("current_tasks", [])


def test_evaluator_cannot_be_implementation_actor(tmp_path: Path):
    project = _write_task(tmp_path)
    CanonicalStateWriter(project).claim("TASK-1", "developer")
    handoffs = HandoffStore(project)
    handoffs.submit(
        "TASK-1",
        "implementation",
        {
            "status": "pass",
            "summary": "done",
            "evidence": ["pytest"],
            "verification": {"acceptance": "pass"},
        },
        role="developer",
        actor="agent-1",
    )
    handoffs.submit(
        "TASK-1",
        "review",
        {"status": "pass", "summary": "reviewed"},
        role="reviewer",
        actor="agent-2",
    )

    with pytest.raises(PermissionError):
        EvaluationService(project).evaluate(
            "TASK-1",
            {"decision": "PASS", "summary": "complete"},
            actor="agent-1",
        )


def test_rework_returns_active_task_to_ready(tmp_path: Path):
    project = _write_task(tmp_path)
    CanonicalStateWriter(project).claim("TASK-1", "developer")
    HandoffStore(project).submit(
        "TASK-1",
        "implementation",
        {"status": "fail", "summary": "needs rework"},
        role="developer",
        actor="developer-1",
    )

    EvaluationService(project).evaluate(
        "TASK-1",
        {"decision": "REWORK", "summary": "fix issues"},
        actor="evaluator-1",
    )

    assert project.backlog()["tasks"][0]["status"] == "ready"


def test_human_gate_blocks_task_and_sets_project_gate(tmp_path: Path):
    project = _write_task(tmp_path)
    CanonicalStateWriter(project).claim("TASK-1", "developer")
    HandoffStore(project).submit(
        "TASK-1",
        "implementation",
        {"status": "blocked", "summary": "needs product decision"},
        role="developer",
        actor="developer-1",
    )

    EvaluationService(project).evaluate(
        "TASK-1",
        {"decision": "HUMAN_GATE", "summary": "needs product decision"},
        actor="evaluator-1",
    )

    assert project.backlog()["tasks"][0]["status"] == "blocked"
    state = project.current_state()
    assert state["human_gate"] is True
    assert state["blocked_tasks"] == ["TASK-1"]


def test_evaluation_requires_active_task(tmp_path: Path):
    project = _write_task(tmp_path, status="ready")
    handoffs = HandoffStore(project)
    handoffs.submit(
        "TASK-1",
        "implementation",
        {"status": "fail", "summary": "not claimed"},
        role="developer",
        actor="developer-1",
    )

    with pytest.raises(ValueError, match="must be active"):
        EvaluationService(project).evaluate(
            "TASK-1",
            {"decision": "REWORK", "summary": "retry"},
            actor="evaluator-1",
        )
