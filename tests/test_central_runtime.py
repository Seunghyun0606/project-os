import asyncio
from pathlib import Path

from projectctl.central_runtime import (
    SqliteApprovalGateway,
    SqliteCheckpointStore,
    SqliteEventStore,
)
from projectctl.central_store import CentralControlStore
from projectctl.control_service import CentralControlService
from projectctl.orchestrator import NativeOrchestrator
from projectctl.runner import CallableAgentRunner
from projectctl.scaffold import install_scaffold


def _setup(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    install_scaffold(root, project_id="demo", project_name="Demo")
    store = CentralControlStore(tmp_path / "control.db")
    control = CentralControlService(store)
    control.register_project(root)
    return root, store, control


def test_native_orchestrator_can_use_central_runtime_backend(tmp_path: Path):
    root, store, control = _setup(tmp_path)
    workflow = root / ".project-os/workflows/demo.yaml"
    workflow.write_text(
        """
id: demo
steps:
  - id: implement
    role: developer
""".strip()
        + "\n",
        encoding="utf-8",
    )
    control.start_run("demo", "run-central", workflow="demo")
    backlog_path = root / ".project-os/state/backlog.yaml"
    state_path = root / ".project-os/state/current.yaml"
    backlog_before = backlog_path.read_text(encoding="utf-8")
    state_before = state_path.read_text(encoding="utf-8")

    async def handler(role, task, context):
        return {"role": role, "ok": True}

    orchestrator = NativeOrchestrator(
        CallableAgentRunner(handler),
        checkpoint_store=SqliteCheckpointStore(store),
        event_store=SqliteEventStore(store, project_id="demo"),
        approval_gateway=SqliteApprovalGateway(store),
    )

    result = asyncio.run(
        orchestrator.execute("demo", root, run_id="run-central")
    )

    assert result["status"] == "COMPLETED"
    assert store.get_run("run-central")["status"] == "COMPLETED"
    assert store.load_checkpoint("run-central")["status"] == "COMPLETED"
    events = store.read_events("run-central")
    assert events[0]["project_id"] == "demo"
    assert events[-1]["type"] == "workflow_completed"
    assert backlog_path.read_text(encoding="utf-8") == backlog_before
    assert state_path.read_text(encoding="utf-8") == state_before
    assert not (
        root / ".project-os/runs/runtime/checkpoints/run-central.yaml"
    ).exists()


def test_central_approval_pause_resume_updates_run_ledger(tmp_path: Path):
    root, store, control = _setup(tmp_path)
    workflow = root / ".project-os/workflows/gated.yaml"
    workflow.write_text(
        """
id: gated
steps:
  - id: release
    role: developer
    approval_gate: production-release
""".strip()
        + "\n",
        encoding="utf-8",
    )
    control.start_run("demo", "run-gated", workflow="gated")

    calls = []

    async def handler(role, task, context):
        calls.append(role)
        return {"released": True}

    approvals = SqliteApprovalGateway(store)
    orchestrator = NativeOrchestrator(
        CallableAgentRunner(handler),
        checkpoint_store=SqliteCheckpointStore(store),
        event_store=SqliteEventStore(store, project_id="demo"),
        approval_gateway=approvals,
    )

    waiting = asyncio.run(
        orchestrator.execute("gated", root, run_id="run-gated")
    )

    assert waiting["status"] == "WAITING_APPROVAL"
    assert store.get_run("run-gated")["status"] == "WAITING_APPROVAL"
    assert calls == []

    approval_id = waiting["pending_approval"]["approval_id"]
    approvals.resolve(approval_id, "approved")

    completed = asyncio.run(
        orchestrator.execute("gated", root, run_id="run-gated")
    )

    assert completed["status"] == "COMPLETED"
    assert store.get_run("run-gated")["status"] == "COMPLETED"
    assert calls == ["developer"]
