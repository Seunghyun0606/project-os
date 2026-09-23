# Architecture

## Purpose

Project OS is a project-management scaffold for long-running agent work. It owns project memory, task contracts, quality policy and deterministic state rules.

It does **not** own remote execution, messenger gateways, host routing or machine lifecycle.

## Layers

```text
Consumer Project
  PROJECT.md + .project-os
          |
      projectctl
          |
  deterministic core
          |
  optional adapters
```

The core must remain usable without an LLM.

## Canonical project memory

Canonical project memory lives in the consumer Git repository:

- PROJECT.md
- specs/
- .project-os/state/
- .project-os/milestones/
- .project-os/tasks/
- .project-os/decisions/
- .project-os/quality/
- durable task results and selected run summaries that the project chooses to commit

Agent conversation history is not canonical project memory.

## Phase 6 contracts

The following contracts are defined before their full backends exist:

- ProjectStore
- TaskScheduler
- ContextBuilder
- AgentRunner
- Orchestrator
- CheckpointStore
- EventStore
- ApprovalGateway

This keeps Project OS independent from Codex, OpenAI Agents SDK, LangGraph, Claude, Gemini or future runtimes.

## State separation

Project state and workflow execution state must remain separate.

- Project state: Git-managed, durable over months, portable between agents.
- Workflow state: run-specific checkpoint/retry/wait information under `.project-os/runs/runtime/` or an equivalent adapter-owned store.

A future LangGraph checkpoint or Agents SDK session must never replace `.project-os` as the project source of truth.

## Single-writer principle

Parallel workers should submit structured results. Canonical state transitions should be performed by one controller path after validation.

This prevents worktree and multi-agent state conflicts.


## Native orchestration

The native Phase 4 runtime is intentionally sequential and small. It exists to prove the orchestration contracts before adopting a larger framework.

```text
workflow YAML
    |
NativeOrchestrator
    |
    +-- AgentRunner
    +-- CheckpointStore
    +-- EventStore
    +-- ApprovalGateway
```

The orchestrator never mutates canonical project state directly. Any future business workflow that needs to change task state must go through the Phase 3 validated handoff and single-writer path.


## Multi-harness application boundary

Phase 5 adds a harness-neutral application service:

```text
CLI -------\
MCP --------> ProjectService -> scheduler/context/handoffs/quality/state writer
Other -----/
```

Adapters may translate protocol shapes, but they must not implement their own scheduling, permissions, quality decisions or YAML mutation logic.

The MCP adapter deliberately exposes business-intent tools and no unrestricted file/state mutation surface.


## Central control plane

Phase 6 adds an optional control plane above multiple consumer repositories.

```text
repo A ---\
repo B ----> CentralControlService ---> SQLite operational metadata
repo C ---/             |
                        +--> central checkpoint/event/approval adapters
```

The registry stores compact snapshots and paths, not copies of project planning documents.

Central operational data includes runs, events, usage/cost and evaluation history. Canonical project state remains in each Git repository.

The control database has an independent schema version through SQLite `PRAGMA user_version`. Consumer schema compatibility and migration need are observed centrally, but consumer files are not automatically upgraded or overwritten.

The default control DB lives outside consumer repositories at `~/.project-os/control.db`.
