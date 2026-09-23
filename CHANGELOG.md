# Changelog

## Unreleased

## 0.3.0 - 2026-09-24

- Add persistent Project Sessions so multiple Jobs can reuse one Codex thread across remote and Desktop channels.
- Add control DB schema v2 with ordered v1→v2 migration for Session and Job operational metadata.
- Capture and persist `thread.started.thread_id`, verify resume identity, and recover once to a fresh Session when a stored Codex thread is stale or missing.
- Add per-Session locking, stale-lock recovery, manual rollover, Job observability and restart persistence.
- Add safe Codex CLI argument construction with shared `CODEX_HOME` resolution and no shell-string interpolation.
- Add `projectctl sessions` plus `projectctl session show/new/attach` and worker integration commands.
- Add transport-neutral `/session`, `/session new` and `/sessions` command handling for Remote Control gateways.
- Add tests for first/second Job reuse, project switching, resume failure recovery, concurrency, restart persistence, Desktop attach and Codex executor behavior.
- Keep consumer scaffold `0.2.0` and canonical schema `1` unchanged; Session state remains replaceable central operational metadata.

## 0.2.0 - 2026-09-23

- Add role-aware bounded context retrieval with project overrides, context-index lookup, active decisions and dependency result summaries.
- Add package compatibility checks to `projectctl doctor`.
- Add tests for context boundaries, token budgets and submit-without-completion behavior.
- Add deterministic run-history compaction with reversible raw-history archiving.
- Add Phase 3 role permission resolution, structured implementation/review/QA/evaluation handoffs and actor separation.
- Centralize claim/evaluation canonical task-state transitions behind a single writer.
- Add prototype and production quality profiles plus deterministic configured-gate evaluation.
- Add framework-neutral Phase 4 native orchestration with file checkpoints, JSONL events and approvals.
- Add step-level failure resume and approval pause/resume without mutating canonical project state.
- Add Phase 5 harness-neutral ProjectService and versioned result envelope.
- Route CLI business actions through the shared service and add separate automated test evidence.
- Add a thin MCP-compatible business-tool adapter with no MCP transport dependency or unrestricted mutation tools.
- Add Phase 6 SQLite central control service for multi-project registry and operational metadata.
- Add central run/event/checkpoint/approval adapters, model policy and role-level cost accounting.
- Add central evaluation history and non-mutating schema migration/compatibility assessment.
- Add tests proving consumer repositories remain readable without the central database.

## 0.1.0 - 2026-09-23

- Initial consumer scaffold.
- Initial projectctl core/CLI.
- Phase 6 extension contracts and versioning model.
