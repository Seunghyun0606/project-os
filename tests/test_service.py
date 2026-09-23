from pathlib import Path

import yaml

from projectctl.project import Project
from projectctl.quality import QualityGateEvaluator
from projectctl.scaffold import install_scaffold
from projectctl.service import ProjectService


def _project(tmp_path: Path) -> Project:
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    backlog = tmp_path / ".project-os/state/backlog.yaml"
    backlog.write_text(
        yaml.safe_dump({
            "tasks": [{
                "id": "TASK-1",
                "title": "Implement",
                "role": "developer",
                "priority": "P0",
                "status": "ready",
                "acceptance": ["works"],
            }]
        }, sort_keys=False),
        encoding="utf-8",
    )
    return Project(tmp_path)


def test_service_returns_stable_harness_envelope(tmp_path: Path):
    service = ProjectService(_project(tmp_path))

    result = service.get_status()

    assert result.version == 1
    assert result.ok is True
    assert result.action == "get_status"
    assert result.error is None
    assert result.data["project_id"] == "demo"


def test_service_returns_structured_error_instead_of_harness_exception(tmp_path: Path):
    service = ProjectService(_project(tmp_path))

    result = service.build_context("TASK-NOPE")

    assert result.ok is False
    assert result.action == "build_context"
    assert result.error.code == "not_found"


def test_service_claim_and_submit_use_existing_core_rules(tmp_path: Path):
    project = _project(tmp_path)
    service = ProjectService(project)

    claimed = service.claim_task("TASK-1", "developer")
    submitted = service.submit_result(
        "TASK-1",
        {
            "status": "pass",
            "summary": "implemented",
            "evidence": ["manual check"],
        },
        actor="dev-1",
    )

    assert claimed.ok is True
    assert submitted.ok is True
    assert project.backlog()["tasks"][0]["status"] == "active"
    stored = yaml.safe_load(
        (tmp_path / ".project-os/tasks/results/TASK-1.yaml").read_text(encoding="utf-8")
    )
    assert stored["actor"] == "dev-1"
    assert stored["kind"] == "implementation"


def test_record_test_result_is_separate_and_feeds_quality_gates(tmp_path: Path):
    project = _project(tmp_path)
    service = ProjectService(project)
    service.claim_task("TASK-1", "developer")
    service.submit_result(
        "TASK-1",
        {"status": "pass", "summary": "implemented", "evidence": ["acceptance checked"]},
        actor="dev-1",
    )

    gates_path = tmp_path / ".project-os/quality/gates.yaml"
    gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
    gates["required"]["unit_test"] = True
    gates["required"]["independent_review"] = False
    gates["required"]["acceptance_evidence"] = True
    gates_path.write_text(yaml.safe_dump(gates, sort_keys=False), encoding="utf-8")

    before = QualityGateEvaluator(project).check("TASK-1")
    recorded = service.record_test_result(
        "TASK-1",
        {
            "status": "pass",
            "summary": "pytest passed",
            "verification": {"unit_test": "pass"},
        },
        actor="ci",
    )
    after = QualityGateEvaluator(project).check("TASK-1")

    assert before["passed"] is False
    assert "unit_test" in before["failed"]
    assert recorded.ok is True
    assert recorded.data["path"].endswith("TASK-1.tests.yaml")
    assert after["passed"] is True

    implementation = yaml.safe_load(
        (tmp_path / ".project-os/tasks/results/TASK-1.yaml").read_text(encoding="utf-8")
    )
    assert "verification" not in implementation


def test_service_rejects_worker_self_review(tmp_path: Path):
    project = _project(tmp_path)
    service = ProjectService(project)
    service.claim_task("TASK-1", "developer")
    service.submit_result(
        "TASK-1",
        {"status": "pass", "summary": "implemented", "evidence": ["done"]},
        actor="same-agent",
    )

    reviewed = service.submit_review(
        "TASK-1",
        {"status": "pass", "summary": "approved"},
        actor="same-agent",
    )

    assert reviewed.ok is False
    assert reviewed.error.code == "permission_denied"
