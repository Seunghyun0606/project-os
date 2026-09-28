# Project Agent Bootstrap

This repository uses Project OS.

Project memory is stored in the repository. Do not reconstruct project state from conversation history.

## Start of work

1. Read `PROJECT.md`.
2. Read `.project-os/manifest.yaml`.
3. Read `.project-os/state/current.yaml`.
4. Determine the current role and task.
5. Load only context required for that role and task.

## During work

- Respect task scope and acceptance criteria.
- Respect project non-goals and active architecture decisions.
- Do not change product direction implicitly.
- Do not mark work complete only because implementation exists.
- Prefer automated verification over self-assessment.
- Escalate only when a configured Human Gate is reached or progress is genuinely blocked.

## Completion

Produce a structured task result. Canonical project state must be updated only through the configured Project OS state transition rules.

If no task is assigned, use `projectctl next --role <role>` to identify an eligible task.

## Optional QA completion contract

If `scripts/qa.ps1` exists, it is the project QA entry point.

Before reporting implementation complete:

1. Run the QA entry point after implementation.
2. A QA `FAIL` is not completion. Analyze the failure, fix what is in scope, and rerun within a reasonable retry limit.
3. If automatic checks pass but visual judgment is still needed, preserve `UI_REVIEW_REQUIRED` and report the generated artifacts for human review.
4. Always report the QA run id, run status, result.json path and relevant artifact paths.
5. If QA cannot run because of an environment/tooling problem, do not treat it as `PASS`.
6. Do not convert `UI_REVIEW_REQUIRED` into `UI_APPROVED` or `UI_REJECTED`; those belong to the external Human Gate / Remote Control layer.

The QA runner contract is project-agnostic. Project-specific tools and commands stay inside the project's QA implementation.
