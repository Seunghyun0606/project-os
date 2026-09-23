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
- context policy inheritance
- context index
- code-map adapters
- decision retrieval
- task-result summaries
- history compaction rules
- token budgets

## Phase 3 - Role-based multi-agent execution

Goal: separate planning, implementation, review, QA and evaluation.

Deliver:
- role contracts
- permission policy
- single-writer canonical state
- structured handoffs
- independent review

## Phase 4 - Orchestration abstraction

Goal: support long-running workflows without binding Project OS to one framework.

Deliver:
- AgentRunner contract
- Orchestrator contract
- CheckpointStore contract
- ApprovalGateway
- native runner first
- optional Agents SDK/LangGraph adapters later

## Phase 5 - Multi-harness integration

Goal: let Codex, Claude Code, Cursor and other harnesses use the same project contract.

Deliver:
- optional MCP adapter
- CLI remains supported
- role-based tool surface
- harness-neutral result format

## Phase 6 - Central project control service

Goal: manage many Project OS repositories and agent runs centrally without moving canonical project memory out of Git.

Deliver:
- project registry
- central run/event ledger
- model policy and cost accounting
- centralized orchestration adapters
- metrics and eval history
- migration/compatibility management

The central service may use a database for runtime metadata, but `.project-os` remains the canonical project state.
