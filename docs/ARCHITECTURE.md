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
- .project-os/runs/

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
- Workflow state: run-specific checkpoint/retry/wait information, owned by an orchestration adapter.

A future LangGraph checkpoint or Agents SDK session must never replace `.project-os` as the project source of truth.

## Single-writer principle

Parallel workers should submit structured results. Canonical state transitions should be performed by one controller path after validation.

This prevents worktree and multi-agent state conflicts.
