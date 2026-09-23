# Detailed implementation prompt

Use the following prompt to continue building this repository with Codex or another coding agent.

---

You are implementing **Project OS** in the repository `Seunghyun0606/project-os`.

## Goal

Build a reusable scaffold and deterministic control layer that lets AI agents continue long-running projects across sessions without repeatedly receiving the same project prompt, while maintaining a configurable quality floor.

Project OS is responsible for **project management and durable project memory**.

Remote execution, messenger integration, Desktop/Lightsail host routing, wake/sleep control, Telegram/Slack gateways and remote worker lifecycle are explicitly out of scope and belong to a separate project.

## Core principles

1. Git-managed project files are the durable project memory.
2. Conversation history is temporary and must not be required to recover project state.
3. Other projects must receive only the consumer scaffold, not Project OS development files.
4. Deterministic decisions belong in code, not repeated LLM prompts.
5. Agents should be stateless where possible; the project should be stateful.
6. A worker agent must not approve its own output.
7. Quality is enforced by evidence and gates, not by an agent saying work is complete.
8. Context must be role/task-specific to reduce token waste.
9. Project OS must not depend on one model, Codex, Agents SDK, LangGraph, MCP or cloud provider.
10. Project state and workflow runtime/checkpoint state must remain separate.
11. Parallel workers submit structured results; canonical state follows a single-writer path.
12. Remote-control concerns must not leak into Project OS.

## Repository boundary

Consumer files live only under:

`scaffold/default/`

Project OS development/versioning files live outside that directory:

- src/
- defaults/
- schemas/
- docs/
- tests/
- VERSION
- CHANGELOG.md
- pyproject.toml
- CI files

`projectctl init` must copy only the consumer scaffold into another repository.

Do not require consumers to copy this entire repository.

## Consumer target

A normal initialized project should look approximately like:

```text
PROJECT.md
AGENTS.md
specs/
.project-os/
  manifest.yaml
  profile.yaml
  state/
    current.yaml
    roadmap.yaml
    backlog.yaml
  milestones/
  tasks/
    ready/
    active/
    blocked/
    completed/
    results/
  decisions/
  quality/
    gates.yaml
  context/
    index.yaml
  runs/
    summaries/
  templates/
```

Do not add Project OS development files to this consumer structure.

## Version model

Maintain three distinct versions:

1. package version
2. scaffold version
3. schema version

Never upgrade an existing project by blindly copying the latest scaffold over canonical state.

Breaking schema changes require ordered migrations.

## Phase 1

Implement and test:

- `projectctl init`
- `projectctl version`
- `projectctl status`
- `projectctl next --role`
- `projectctl context TASK`
- `projectctl claim TASK`
- `projectctl submit TASK RESULT`
- `projectctl doctor`

Rules:

- next must be deterministic.
- ready status is required.
- dependencies must be done.
- task human_gate must be false.
- role must match.
- priority ordering must be deterministic.
- submit stores a result but must not self-approve task completion.
- doctor must detect missing required files, duplicate IDs, missing dependencies and dependency cycles.
- init must preflight overwrite conflicts before writing anything.

## Phase 2

Add context retrieval without loading the whole repository by default.

Implement:

- role-specific context-policy inheritance
- context-index lookup
- active ADR/decision lookup
- optional symbol/code-map adapter
- task-result summaries
- context token-budget enforcement
- compaction of old run history into summaries

Keep retrieval algorithms behind interfaces so they can evolve independently.

## Phase 3

Add structured roles:

- planner
- architect
- developer
- reviewer
- qa
- evaluator

Use global defaults plus project overrides rather than copying long prompts into every project.

Implement permission boundaries, structured handoffs and a single-writer path for canonical project state.

## Phase 4

Do not hard-code LangGraph or OpenAI Agents SDK into the domain model.

Define and test:

- AgentRunner
- Orchestrator
- CheckpointStore
- EventStore
- ApprovalGateway

Start with a simple native implementation.

Add Agents SDK or LangGraph only as adapters when their functionality is actually required.

Project state in Git must never be replaced by orchestration-framework checkpoint state.

## Phase 5

Expose the same core to multiple harnesses.

CLI remains mandatory.

MCP is optional and must be an adapter over projectctl-core, not a second implementation.

If MCP is added, expose business-intent tools such as:

- get_status
- get_next_task
- build_context
- claim_task
- submit_result
- submit_review
- record_test_result
- evaluate_task

Do not expose unrestricted YAML mutation tools.

## Phase 6

Build a central control service for multiple Project OS repositories.

It may own runtime metadata such as:

- project registry
- active runs
- workflow checkpoints
- run/event ledger
- model usage/cost records
- eval history

It must not become the sole source of truth for project planning state.

A fresh clone of a consumer Git repository must still contain enough durable information to understand project direction and current canonical state.

## Quality system

Support profiles such as prototype, standard and production.

Completion should derive from configured gates.

Expected flow:

```text
implementation
 -> automated checks
 -> independent review
 -> QA
 -> evaluator
 -> PASS / REWORK / HUMAN_GATE
```

Human gates must be policy-driven rather than triggered by every ambiguous implementation choice.

## Testing requirements

Every new deterministic rule requires tests.

At minimum cover:

- clean init
- overwrite protection with no partial writes
- root discovery from a nested directory
- deterministic task priority
- dependency blocking
- human-gate blocking
- role filtering
- duplicate task detection
- missing dependency detection
- cycle detection
- context-package boundaries
- result submission without completion
- version compatibility and migration behavior when added

## README requirement

Keep README approachable and in this order:

1. Overview
2. Quick start
3. Detailed guide
4. Scaffold vs Project OS development files
5. Version management
6. Design principles

Avoid unnecessary orchestration jargon in the main README. Put deeper architecture terms under docs/.

## Definition of done

A change is complete only when:

- implementation exists,
- relevant tests pass,
- scaffold/runtime separation remains intact,
- README/docs are updated when user behavior changes,
- no remote-control responsibilities leak into Project OS,
- canonical project data is not silently overwritten.

Proceed autonomously within these boundaries. Stop for human input only when changing product scope, breaking the data contract without a migration plan, or making a destructive change that cannot be recovered safely.
