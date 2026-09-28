# Changelog

## Unreleased

## 0.3.0 - 2026-09-28

- Add project-agnostic QA Result Contract 1.0 with PASS/FAIL/UI_REVIEW_REQUIRED run states and stage-level PASS/FAIL/SKIPPED/REVIEW_REQUIRED semantics.
- Add schema-validated run-relative artifact metadata for screenshots, videos, logs, reports, traces and other evidence.
- Add optional consumer QA overlay with Windows-first scripts/qa.ps1, QA guide, result example and lightweight scenario convention.
- Add projectctl init --with-qa for fresh projects and projectctl qa-init for existing Project OS projects without reinstalling the base scaffold.
- Add Codex completion rules that require configured QA to run before completion and preserve the boundary between automated checks and human UI approval.
- Add Windows PowerShell 5.1 scaffold smoke coverage and JSON Schema regression tests.
- Keep Remote Control orchestration, Telegram, Human Gate actions and project-specific test implementations out of Project OS.


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
