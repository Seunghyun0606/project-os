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

If `.qa/manifest.yaml` exists, the project declares support for the Project OS QA Contract.

For code changes covered by QA:

1. Read `.qa/manifest.yaml` and run the command for the current host OS after implementation.
2. A QA `FAIL` is not completion. Analyze the failure, fix what is in scope, and rerun within a reasonable retry limit.
3. `PASS_WITH_WARNINGS` may be completed only when warnings are reported explicitly with their artifacts.
4. Preserve `HUMAN_GATE_REQUIRED` and report the relevant artifacts. Do not self-approve the human gate.
5. Always report the QA run id, status, result path, and important/failure artifacts.
6. If QA cannot run because the environment is unavailable, do not treat it as `PASS`.

QA may be skipped only when the change is documentation-only, modifies the QA environment itself, no executable QA environment exists, or the task explicitly excludes QA. State the reason when skipping.

The QA runner contract is project-agnostic. Project-specific tools and commands stay inside the project's QA implementation.
