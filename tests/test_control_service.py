from pathlib import Path

import yaml

from projectctl.central_store import CentralControlStore
from projectctl.control_service import CentralControlService
from projectctl.scaffold import install_scaffold


def _project(tmp_path: Path, project_id: str = "demo") -> Path:
    root = tmp_path / project_id
    root.mkdir()
    install_scaffold(root, project_id=project_id, project_name=project_id.title())
    return root


def test_register_and_sync_observe_repo_without_mutating_canonical_files(tmp_path: Path):
    root = _project(tmp_path)
    store = CentralControlStore(tmp_path / "control.db")
    service = CentralControlService(store)

    backlog_path = root / ".project-os/state/backlog.yaml"
    project_path = root / "PROJECT.md"
    backlog_before = backlog_path.read_text(encoding="utf-8")
    project_before = project_path.read_text(encoding="utf-8")

    registered = service.register_project(root)

    assert registered["project_id"] == "demo"
    assert registered["root_path"] == root.resolve().as_posix()
    assert registered["compatibility_status"] == "compatible"
    assert backlog_path.read_text(encoding="utf-8") == backlog_before
    assert project_path.read_text(encoding="utf-8") == project_before

    state_path = root / ".project-os/state/current.yaml"
    state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    state["project_status"] = "paused"
    state["current_milestone"] = "M2"
    state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")

    synced = service.sync_project("demo")

    assert synced["project_status"] == "paused"
    assert synced["current_milestone"] == "M2"
    assert backlog_path.read_text(encoding="utf-8") == backlog_before
    assert project_path.read_text(encoding="utf-8") == project_before


def test_control_service_tracks_runs_model_policy_usage_and_eval_history(tmp_path: Path):
    root = _project(tmp_path)
    service = CentralControlService(CentralControlStore(tmp_path / "control.db"))
    service.register_project(root)

    run = service.start_run(
        project_id="demo",
        run_id="run-1",
        workflow="build",
        metadata={"source": "test"},
    )
    policy = service.set_model_policy(
        project_id="demo",
        role="developer",
        provider="openai",
        model="gpt-test",
        max_cost=5.0,
        config={"reasoning": "medium"},
    )
    summary = service.record_usage(
        project_id="demo",
        run_id="run-1",
        provider="openai",
        model="gpt-test",
        input_tokens=100,
        output_tokens=20,
        cost=0.25,
    )
    summary = service.record_usage(
        project_id="demo",
        run_id="run-1",
        provider="openai",
        model="gpt-test",
        input_tokens=50,
        output_tokens=10,
        cost=0.10,
    )
    history = service.record_evaluation(
        project_id="demo",
        task_id="TASK-1",
        run_id="run-1",
        decision="PASS",
        metrics={"critical_issues": 0},
    )

    assert run["status"] == "RUNNING"
    assert policy["provider"] == "openai"
    assert policy["config"] == {"reasoning": "medium"}
    assert summary["input_tokens"] == 150
    assert summary["output_tokens"] == 30
    assert summary["cost_by_currency"]["USD"] == 0.35
    assert history[-1]["decision"] == "PASS"
    assert history[-1]["metrics"] == {"critical_issues": 0}


def test_migration_assessment_is_observational_only(tmp_path: Path):
    root = _project(tmp_path)
    service = CentralControlService(CentralControlStore(tmp_path / "control.db"))
    service.register_project(root)

    manifest_path = root / ".project-os/manifest.yaml"
    before = manifest_path.read_text(encoding="utf-8")

    status = service.assess_migration("demo", "2")

    assert status["status"] == "migration_required"
    assert status["observed_schema_version"] == "1"
    assert status["target_schema_version"] == "2"
    assert manifest_path.read_text(encoding="utf-8") == before


def test_dashboard_aggregates_registry_and_active_runs(tmp_path: Path):
    service = CentralControlService(CentralControlStore(tmp_path / "control.db"))
    one = _project(tmp_path, "one")
    two = _project(tmp_path, "two")
    service.register_project(one)
    service.register_project(two)
    service.start_run("one", "run-one")
    service.start_run("two", "run-two")
    service.update_run("run-two", "COMPLETED")

    dashboard = service.dashboard()

    assert dashboard["project_count"] == 2
    assert dashboard["active_run_count"] == 1
    assert dashboard["active_runs"][0]["run_id"] == "run-one"
