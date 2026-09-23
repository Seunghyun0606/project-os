import asyncio
from pathlib import Path

import yaml

from projectctl.orchestrator import NativeOrchestrator
from projectctl.runner import CallableAgentRunner
from projectctl.runtime_stores import FileApprovalGateway, FileCheckpointStore, FileEventStore
from projectctl.scaffold import install_scaffold


def _workflow(tmp_path: Path, content: str):
    path = tmp_path / ".project-os/workflows/demo.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_native_orchestrator_completes_and_leaves_canonical_state_unchanged(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    _workflow(
        tmp_path,
        """
id: demo
steps:
  - id: one
    role: developer
    task:
      id: TASK-1
  - id: two
    role: reviewer
""",
    )

    backlog_path = tmp_path / ".project-os/state/backlog.yaml"
    state_path = tmp_path / ".project-os/state/current.yaml"
    backlog_before = backlog_path.read_text(encoding="utf-8")
    state_before = state_path.read_text(encoding="utf-8")
    calls = []

    async def handler(role, task, context):
        calls.append((role, task, context))
        return {"role": role, "ok": True}

    result = asyncio.run(
        NativeOrchestrator(CallableAgentRunner(handler)).execute(
            "demo",
            tmp_path,
            run_id="run-1",
        )
    )

    assert result["status"] == "COMPLETED"
    assert result["completed_steps"] == ["one", "two"]
    assert [call[0] for call in calls] == ["developer", "reviewer"]
    assert backlog_path.read_text(encoding="utf-8") == backlog_before
    assert state_path.read_text(encoding="utf-8") == state_before

    checkpoint = FileCheckpointStore(tmp_path).load_checkpoint("run-1")
    assert checkpoint["status"] == "COMPLETED"
    events = FileEventStore(tmp_path).read_events("run-1")
    assert [event["type"] for event in events] == [
        "workflow_started",
        "step_started",
        "step_completed",
        "step_started",
        "step_completed",
        "workflow_completed",
    ]


def test_native_orchestrator_resumes_from_failed_step(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    _workflow(
        tmp_path,
        """
id: demo
steps:
  - id: one
    role: developer
  - id: two
    role: reviewer
""",
    )

    calls = {"one": 0, "two": 0}

    async def handler(role, task, context):
        step = "one" if role == "developer" else "two"
        calls[step] += 1
        if step == "two" and calls[step] == 1:
            raise RuntimeError("temporary failure")
        return {"step": step}

    orchestrator = NativeOrchestrator(CallableAgentRunner(handler))
    first = asyncio.run(orchestrator.execute("demo", tmp_path, run_id="run-retry"))
    second = asyncio.run(orchestrator.execute("demo", tmp_path, run_id="run-retry"))

    assert first["status"] == "FAILED"
    assert second["status"] == "COMPLETED"
    assert calls == {"one": 1, "two": 2}
    assert second["completed_steps"] == ["one", "two"]


def test_native_orchestrator_waits_for_and_resumes_after_approval(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    _workflow(
        tmp_path,
        """
id: demo
steps:
  - id: deploy
    role: developer
    approval_gate: production-release
""",
    )

    calls = []

    async def handler(role, task, context):
        calls.append(role)
        return {"deployed": True}

    orchestrator = NativeOrchestrator(CallableAgentRunner(handler))
    waiting = asyncio.run(
        orchestrator.execute("demo", tmp_path, run_id="run-approval")
    )

    assert waiting["status"] == "WAITING_APPROVAL"
    assert calls == []
    approval_id = waiting["pending_approval"]["approval_id"]

    FileApprovalGateway(tmp_path).resolve(approval_id, "approved")
    completed = asyncio.run(
        orchestrator.execute("demo", tmp_path, run_id="run-approval")
    )

    assert completed["status"] == "COMPLETED"
    assert calls == ["developer"]


def test_approved_gate_is_not_requested_again_when_step_retries(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    _workflow(
        tmp_path,
        """
id: demo
steps:
  - id: deploy
    role: developer
    approval_gate: production-release
""",
    )

    attempts = 0

    async def handler(role, task, context):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("transient")
        return {"ok": True}

    orchestrator = NativeOrchestrator(CallableAgentRunner(handler))
    waiting = asyncio.run(
        orchestrator.execute("demo", tmp_path, run_id="run-approved-retry")
    )
    approval_id = waiting["pending_approval"]["approval_id"]
    FileApprovalGateway(tmp_path).resolve(approval_id, "approved")

    failed = asyncio.run(
        orchestrator.execute("demo", tmp_path, run_id="run-approved-retry")
    )
    completed = asyncio.run(
        orchestrator.execute("demo", tmp_path, run_id="run-approved-retry")
    )

    assert failed["status"] == "FAILED"
    assert completed["status"] == "COMPLETED"
    events = FileEventStore(tmp_path).read_events("run-approved-retry")
    assert [event["type"] for event in events].count("approval_requested") == 1


def test_rejected_approval_ends_workflow_without_running_step(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    _workflow(
        tmp_path,
        """
id: demo
steps:
  - id: deploy
    role: developer
    approval_gate: production-release
""",
    )

    calls = []

    async def handler(role, task, context):
        calls.append(role)
        return {"ok": True}

    orchestrator = NativeOrchestrator(CallableAgentRunner(handler))
    waiting = asyncio.run(orchestrator.execute("demo", tmp_path, run_id="run-reject"))
    approval_id = waiting["pending_approval"]["approval_id"]
    FileApprovalGateway(tmp_path).resolve(approval_id, "rejected")

    rejected = asyncio.run(orchestrator.execute("demo", tmp_path, run_id="run-reject"))

    assert rejected["status"] == "REJECTED"
    assert calls == []
