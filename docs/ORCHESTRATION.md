# Native orchestration

Project OS Phase 4 provides a small framework-neutral workflow runtime.

It is intentionally not a replacement for canonical project state and does not depend on LangGraph, OpenAI Agents SDK, Codex, Claude or a cloud provider.

## Runtime boundary

Canonical project memory remains:

```text
PROJECT.md
specs/
.project-os/state/
.project-os/milestones/
.project-os/tasks/
.project-os/decisions/
.project-os/quality/
```

Workflow execution metadata is separate:

```text
.project-os/
  workflows/
  runs/
    runtime/
      checkpoints/
      events/
      approvals/
```

Deleting `runs/runtime/` loses workflow resume information, but it must not make the project direction or canonical task state unknowable.

## Contracts

Phase 4 defines:

- `AgentRunner`
- `Orchestrator`
- `CheckpointStore`
- `EventStore`
- `ApprovalGateway`

The native implementations are deliberately small:

- `CallableAgentRunner`
- `NativeOrchestrator`
- `FileCheckpointStore`
- `FileEventStore`
- `FileApprovalGateway`
- `FileWorkflowRegistry`

A future LangGraph or Agents SDK integration should implement these contracts or adapt to them rather than replacing Project OS project state.

## Workflow file

A native workflow is a small YAML file under `.project-os/workflows/`.

Example:

```yaml
id: implementation-review
steps:
  - id: implement
    role: developer
    task:
      id: TASK-001
    context:
      purpose: implement the task

  - id: release
    role: developer
    approval_gate: production-release
    context:
      purpose: release after human approval
```

The native workflow runner is generic. It does not assume that a workflow step is an LLM call. The injected `AgentRunner` decides how a role is executed.

## Native runner example

```python
import asyncio

from projectctl.orchestrator import NativeOrchestrator
from projectctl.runner import CallableAgentRunner


async def handler(role, task, context):
    return {
        "role": role,
        "task": task,
        "result": "ok",
    }


runner = CallableAgentRunner(handler)
orchestrator = NativeOrchestrator(runner)

result = asyncio.run(
    orchestrator.execute(
        "implementation-review",
        project_root,
        run_id="run-001",
    )
)
```

The caller should retain the returned `run_id`. Passing the same run id again resumes from the latest durable checkpoint.

## Failure and resume

A checkpoint is written after every completed step.

If step 3 fails:

```text
step 1 -> complete
step 2 -> complete
step 3 -> failed
```

re-running with the same `run_id` starts again from step 3. Completed steps are not re-executed.

Failures are runtime state only. They do not modify canonical backlog/task state.

## Human approval

A workflow step can declare `approval_gate`.

The orchestrator then returns:

```text
WAITING_APPROVAL
```

without running the step.

Inspect or resolve the approval with:

```bash
projectctl runtime-status run-001
projectctl approval-status approval-...
projectctl approval-resolve approval-... approved
```

Then call the orchestrator again with the same `run_id`.

Rejected approval ends that runtime as `REJECTED`.

Approved gates are stored in the checkpoint, so a transient execution failure after approval does not require the same approval again.

## Events

Runtime events use JSON Lines under `runs/runtime/events/`.

Examples:

- workflow_started
- workflow_resumed
- step_started
- step_completed
- step_failed
- approval_requested
- approval_approved
- approval_rejected
- workflow_completed

These events are an execution ledger. They are not a substitute for task contracts, handoffs or canonical project state.

## Adapter rule

Framework adapters may own richer checkpoint data, retries, streaming and sessions.

They must preserve these boundaries:

1. Project OS Git state remains the durable project source of truth.
2. Runtime checkpoint state remains replaceable.
3. Worker execution must not bypass Phase 3 handoff and canonical-state rules.
4. Remote hosts, messenger gateways and machine lifecycle remain outside this repository.


## Project Session is not a workflow run

Persistent Project Sessions and native workflow `run_id` solve different problems.

- Session: reuse one agent conversation context across many user Jobs and channels.
- Workflow run: resume a deterministic multi-step orchestration checkpoint.

A Job may participate in both, but neither identifier replaces the other. Session loss must be recoverable from canonical project state, while workflow checkpoints remain replaceable runtime state.
