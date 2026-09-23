# Project OS delivery phases

Remote execution is deliberately excluded from these phases.

## Phase 0 - Manual scaffold

Goal: prove repository-based project memory.

Deliver:
- PROJECT.md
- AGENTS.md
- .project-os state/roadmap/backlog
- milestones/tasks/decisions/quality layout

## Phase 1 - projectctl core + CLI

Goal: remove deterministic decisions from LLM prompts.

Deliver:
- init
- version
- status
- next
- context
- claim
- submit
- doctor

## Phase 2 - Context and long-term memory

Goal: minimize repeated context and session dependence.

Deliver:
- context policy inheritance — implemented foundation
- context index — implemented foundation
- code-map adapters — interface added
- decision retrieval — implemented foundation
- task-result summaries — implemented for dependency results
- history compaction rules — implemented
- token budgets — implemented foundation

## Phase 3 - Role-based multi-agent execution

Goal: separate planning, implementation, review, QA and evaluation.

Deliver:
- role contracts — implemented
- permission policy — implemented foundation
- single-writer canonical state — implemented for claim/evaluation transitions
- structured handoffs — implemented
- independent review — enforced by actor separation

## Phase 4 - Orchestration abstraction

Goal: support long-running workflows without binding Project OS to one framework.

Deliver:
- AgentRunner contract — implemented
- Orchestrator contract — implemented
- CheckpointStore contract — implemented with file backend
- EventStore contract — implemented with JSONL backend
- ApprovalGateway — implemented with file backend
- native runner first — implemented
- checkpointed failure/resume — implemented
- approval pause/resume — implemented
- optional Agents SDK/LangGraph adapters later — pending until needed

## Phase 5 - Multi-harness integration

Goal: let Codex, Claude Code, Cursor and other harnesses use the same project contract.

Deliver:
- harness-neutral ProjectService — implemented
- optional MCP adapter — implemented without transport dependency
- CLI remains supported — routed through ProjectService for core business actions
- role-based business-intent tool surface — implemented
- harness-neutral result format — implemented and versioned
- separate automated test evidence — implemented

## Phase 6 - Central project control service

Goal: manage many Project OS repositories and agent runs centrally without moving canonical project memory out of Git.

Deliver:
- project registry — implemented with SQLite metadata store
- central run/event ledger — implemented
- model policy and cost accounting — implemented with role-level budget reporting
- centralized orchestration adapters — implemented for checkpoint/event/approval contracts
- metrics and eval history — implemented foundation
- migration/compatibility management — implemented as non-mutating assessment
- versioned central DB schema — implemented

The central service uses SQLite for operational metadata, while `.project-os` remains the canonical project state. Losing the central DB must not make a consumer repository uninterpretable.
