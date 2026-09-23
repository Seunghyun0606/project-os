# Changelog

## Unreleased

- Add role-aware bounded context retrieval with project overrides, context-index lookup, active decisions and dependency result summaries.
- Add package compatibility checks to `projectctl doctor`.
- Add tests for context boundaries, token budgets and submit-without-completion behavior.
- Add deterministic run-history compaction with reversible raw-history archiving.
- Add Phase 3 role permission resolution, structured implementation/review/QA/evaluation handoffs and actor separation.
- Centralize claim/evaluation canonical task-state transitions behind a single writer.
- Add prototype and production quality profiles plus deterministic configured-gate evaluation.
- Add framework-neutral Phase 4 native orchestration with file checkpoints, JSONL events and approvals.
- Add step-level failure resume and approval pause/resume without mutating canonical project state.

## 0.1.0 - 2026-09-23

- Initial consumer scaffold.
- Initial projectctl core/CLI.
- Phase 6 extension contracts and versioning model.
