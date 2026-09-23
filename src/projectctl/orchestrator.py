from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .interfaces import (
    AgentRunner,
    ApprovalGateway,
    CheckpointStore,
    EventStore,
)
from .runtime_stores import FileApprovalGateway, FileCheckpointStore, FileEventStore
from .workflow import FileWorkflowRegistry, WorkflowDefinition


_TERMINAL = {"COMPLETED", "REJECTED"}


class NativeOrchestrator:
    """Framework-neutral sequential workflow runner with durable runtime checkpoints."""

    def __init__(
        self,
        runner: AgentRunner,
        checkpoint_store: CheckpointStore | None = None,
        event_store: EventStore | None = None,
        approval_gateway: ApprovalGateway | None = None,
    ):
        self.runner = runner
        self.checkpoint_store = checkpoint_store
        self.event_store = event_store
        self.approval_gateway = approval_gateway

    def _result(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": state["run_id"],
            "workflow": state["workflow"],
            "status": state["status"],
            "completed_steps": list(state.get("completed_steps", []) or []),
            "outputs": dict(state.get("outputs", {}) or {}),
            "pending_approval": state.get("pending_approval"),
            "error": state.get("error"),
        }

    def _new_state(self, definition: WorkflowDefinition, run_id: str) -> dict[str, Any]:
        return {
            "run_id": run_id,
            "workflow": definition.id,
            "status": "RUNNING",
            "next_step": 0,
            "completed_steps": [],
            "approved_steps": [],
            "outputs": {},
            "pending_approval": None,
            "error": None,
        }

    async def execute(
        self,
        workflow: str,
        project_root: Path,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        root = project_root.resolve()
        definition = FileWorkflowRegistry(root).load(workflow)
        checkpoints = self.checkpoint_store or FileCheckpointStore(root)
        events = self.event_store or FileEventStore(root)
        approvals = self.approval_gateway or FileApprovalGateway(root)

        resolved_run_id = run_id or f"run-{uuid4().hex}"
        state = checkpoints.load_checkpoint(resolved_run_id)
        if state is None:
            state = self._new_state(definition, resolved_run_id)
            checkpoints.save_checkpoint(resolved_run_id, state)
            events.append_event({
                "run_id": resolved_run_id,
                "type": "workflow_started",
                "workflow": definition.id,
            })
        else:
            if state.get("workflow") != definition.id:
                raise ValueError(
                    f"Run {resolved_run_id} belongs to workflow {state.get('workflow')}, "
                    f"not {definition.id}"
                )
            if state.get("status") in _TERMINAL:
                return self._result(state)
            if state.get("status") == "FAILED":
                state["status"] = "RUNNING"
                state["error"] = None
                checkpoints.save_checkpoint(resolved_run_id, state)
                events.append_event({
                    "run_id": resolved_run_id,
                    "type": "workflow_resumed",
                    "workflow": definition.id,
                })

        while int(state.get("next_step", 0)) < len(definition.steps):
            index = int(state.get("next_step", 0))
            step = definition.steps[index]

            if step.approval_gate and step.id not in set(state.get("approved_steps", []) or []):
                pending = state.get("pending_approval")
                if pending and pending.get("step_id") == step.id:
                    approval_id = str(pending["approval_id"])
                    approval_status = approvals.status(approval_id)
                    if approval_status == "pending":
                        state["status"] = "WAITING_APPROVAL"
                        checkpoints.save_checkpoint(resolved_run_id, state)
                        return self._result(state)
                    if approval_status == "rejected":
                        state["status"] = "REJECTED"
                        state["pending_approval"] = None
                        checkpoints.save_checkpoint(resolved_run_id, state)
                        events.append_event({
                            "run_id": resolved_run_id,
                            "type": "approval_rejected",
                            "step_id": step.id,
                            "approval_id": approval_id,
                        })
                        return self._result(state)

                    state["pending_approval"] = None
                    state.setdefault("approved_steps", []).append(step.id)
                    state["status"] = "RUNNING"
                    checkpoints.save_checkpoint(resolved_run_id, state)
                    events.append_event({
                        "run_id": resolved_run_id,
                        "type": "approval_approved",
                        "step_id": step.id,
                        "approval_id": approval_id,
                    })
                else:
                    approval_id = approvals.request(
                        step.approval_gate,
                        {
                            "run_id": resolved_run_id,
                            "workflow": definition.id,
                            "step_id": step.id,
                            "role": step.role,
                        },
                    )
                    state["status"] = "WAITING_APPROVAL"
                    state["pending_approval"] = {
                        "step_id": step.id,
                        "approval_id": approval_id,
                        "gate": step.approval_gate,
                    }
                    checkpoints.save_checkpoint(resolved_run_id, state)
                    events.append_event({
                        "run_id": resolved_run_id,
                        "type": "approval_requested",
                        "step_id": step.id,
                        "approval_id": approval_id,
                        "gate": step.approval_gate,
                    })
                    return self._result(state)

            events.append_event({
                "run_id": resolved_run_id,
                "type": "step_started",
                "step_id": step.id,
                "role": step.role,
            })
            try:
                output = await self.runner.run(
                    step.role,
                    dict(step.task),
                    dict(step.context),
                )
            except Exception as exc:
                state["status"] = "FAILED"
                state["error"] = {
                    "step_id": step.id,
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                checkpoints.save_checkpoint(resolved_run_id, state)
                events.append_event({
                    "run_id": resolved_run_id,
                    "type": "step_failed",
                    "step_id": step.id,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                })
                return self._result(state)

            state.setdefault("outputs", {})[step.id] = output
            state.setdefault("completed_steps", []).append(step.id)
            state["next_step"] = index + 1
            state["status"] = "RUNNING"
            state["error"] = None
            checkpoints.save_checkpoint(resolved_run_id, state)
            events.append_event({
                "run_id": resolved_run_id,
                "type": "step_completed",
                "step_id": step.id,
            })

        state["status"] = "COMPLETED"
        state["pending_approval"] = None
        checkpoints.save_checkpoint(resolved_run_id, state)
        events.append_event({
            "run_id": resolved_run_id,
            "type": "workflow_completed",
            "workflow": definition.id,
        })
        return self._result(state)
