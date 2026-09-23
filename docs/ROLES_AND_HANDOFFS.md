# Roles, handoffs and canonical state

Phase 3 separates worker output from approval and centralizes canonical task-state mutation.

## Roles

Project OS ships global defaults for:

- planner
- architect
- developer
- reviewer
- qa
- evaluator

Each role declares logical read/write capabilities under `defaults/roles/`. A consumer project may override a role under `.project-os/profile.yaml`:

```yaml
overrides:
  roles:
    developer:
      writes:
        - task_result
```

Use `projectctl role-policy developer` to inspect the resolved policy.

## Structured handoffs

Implementation, review, QA and evaluation are separate evidence records.

```text
.project-os/tasks/results/
  TASK-001.yaml
  TASK-001.review.yaml
  TASK-001.qa.yaml
  TASK-001.evaluation.yaml
```

Every stored handoff records:

- task
- kind
- role
- actor

The actor identity may be passed with `--actor` or with `PROJECT_OS_ACTOR`. If neither is supplied, the role name is used as a stable local default.

Reviewer, QA and evaluator handoffs cannot use the same actor identity as the implementation they are checking. The evaluator also cannot reuse the reviewer or QA actor identity when those handoffs exist.

## Single-writer state path

Worker handoffs never mark a task complete.

Canonical task/current-state changes go through `CanonicalStateWriter`:

```text
claim
  -> active

evaluation PASS
  -> done

evaluation REWORK
  -> ready

evaluation HUMAN_GATE
  -> blocked + human_gate
```

Evaluation is allowed only for an active task.

A PASS transition is rejected until every configured quality gate passes.

## CLI flow

```bash
projectctl claim TASK-001 --role developer

projectctl submit TASK-001 implementation.yaml --actor dev-agent-1
projectctl review TASK-001 review.yaml --actor review-agent-1
projectctl qa TASK-001 qa.yaml --actor qa-agent-1
projectctl evaluate TASK-001 evaluation.yaml --actor eval-agent-1
```

QA is required only when the active quality policy requires it.

## Quality profiles

Project OS includes prototype, standard and production quality profiles. The project selects one through `.project-os/profile.yaml`.

Project-specific `.project-os/quality/gates.yaml` and profile overrides are merged on top of the selected default.

This keeps shared policy in Project OS while allowing a project to tighten or relax explicitly configurable gates.
