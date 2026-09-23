# Central control service

Phase 6 adds a local central control plane for people or automation that manage multiple Project OS repositories.

The central service is deliberately **not** the canonical project database.

Each consumer repository remains the source of truth for:

- product direction,
- specs,
- roadmap,
- backlog,
- task contracts,
- decisions,
- quality policy,
- durable task results.

The central database stores operational metadata that is useful across repositories.

## Default location

The default central SQLite database is:

```text
~/.project-os/control.db
```

You can use another location with `--db`.

No central database file is added to the consumer scaffold.

## What the central database stores

Phase 6 stores:

- project registry snapshots,
- active and historical run metadata,
- workflow event ledger,
- workflow checkpoints,
- approval state,
- model routing/cost policy metadata,
- token and cost usage records,
- evaluation history,
- compatibility and migration assessment status,
- persistent Project Session metadata and per-request Job linkage.

It does **not** copy backlog/spec/decision contents into SQLite.

## Register projects

Register one repository:

```bash
projectctl control register /path/to/project
```

List all registered projects:

```bash
projectctl control list
```

Refresh the central snapshot from the repository:

```bash
projectctl control sync my-project
```

Show a small cross-project dashboard:

```bash
projectctl control dashboard
```

The registry snapshot includes only compact information such as project id, name, current status, milestone, human-gate state and Project OS version compatibility.

## Run ledger

Register a run:

```bash
projectctl control run-start my-project run-001 --workflow implementation-review
```

Update a run manually when needed:

```bash
projectctl control run-update run-001 COMPLETED
```

When the Phase 4 `NativeOrchestrator` uses the SQLite runtime adapters, workflow events update the central run status automatically.

Supported run states are:

- RUNNING
- WAITING_APPROVAL
- FAILED
- REJECTED
- COMPLETED
- CANCELLED

## Centralized runtime adapters

Phase 6+ provides:

- `SqliteCheckpointStore`
- `SqliteEventStore`
- `SqliteApprovalGateway`

They implement the same Phase 4 contracts as the local file backends.

Example:

```python
from projectctl.central_runtime import (
    SqliteApprovalGateway,
    SqliteCheckpointStore,
    SqliteEventStore,
)
from projectctl.central_store import CentralControlStore
from projectctl.orchestrator import NativeOrchestrator

store = CentralControlStore("~/.project-os/control.db")

orchestrator = NativeOrchestrator(
    runner,
    checkpoint_store=SqliteCheckpointStore(store),
    event_store=SqliteEventStore(store, project_id="my-project"),
    approval_gateway=SqliteApprovalGateway(store),
)
```

The workflow definition still comes from the consumer repository.

Using a central runtime backend does not give the orchestrator permission to mutate canonical backlog/task state.

## Model policy and cost accounting

Set model metadata for a role:

```bash
projectctl control policy-set \
  my-project developer openai gpt-model \
  --max-cost 10
```

Record usage:

```bash
projectctl control usage-record \
  my-project openai gpt-model \
  --role developer \
  --input-tokens 12000 \
  --output-tokens 2400 \
  --cost 0.42 \
  --run-id run-001
```

Inspect aggregate usage:

```bash
projectctl control usage my-project
```

Inspect the role budget:

```bash
projectctl control budget my-project developer
```

The budget result contains configured maximum cost, amount spent, remaining amount and whether the recorded spend exceeds the configured maximum.

This is accounting/policy metadata. Provider credentials and remote execution are outside Project OS.

## Evaluation history

Record compact evaluation metadata:

```bash
projectctl control eval-record my-project TASK-001 PASS --run-id run-001
```

Read history:

```bash
projectctl control eval-history my-project --task-id TASK-001
```

The canonical evaluation handoff remains in the consumer repository. Central evaluation history is for metrics and cross-project analysis.

## Compatibility and migration management

Registration and sync compare the installed `projectctl` package version to the consumer manifest's `package_compatibility` constraint.

Migration assessment is explicit:

```bash
projectctl control migration-assess my-project 2
```

Possible results include:

- up_to_date
- migration_required
- project_ahead
- invalid_version

Assessment never edits the project.

Actual breaking schema upgrades still require an ordered migration implementation.

## Central database schema

The control database has its own schema version, separate from consumer Project OS schema versions. Current control DB schema version is `2`; opening a v1 DB performs an ordered v1→v2 migration that adds `sessions` and `jobs` without changing consumer repositories.

It is stored with SQLite `PRAGMA user_version`.

The application refuses to open a control database whose schema is newer than the installed code understands.

Future control-database breaking changes must use ordered migrations.

## Failure boundary

The central control database must be treated as replaceable operational metadata.

If it is lost:

1. project direction still exists in Git,
2. backlog/task state still exists in Git,
3. specs and decisions still exist in Git,
4. each repository can be registered again.

Runtime-only history stored exclusively in the central DB may be lost, so production deployments should back it up if that history matters.

This separation is a deliberate Project OS invariant.

## Out of scope

Phase 6+ still does not own Telegram/Slack network gateways, Desktop/Lightsail routing, host wake/sleep, remote shell transport, machine lifecycle or messenger authorization. Those belong to the separate Remote Control system.

Project Session identity/persistence/locking is intentionally owned here so Telegram and Desktop can share one runtime context without either channel becoming the session owner. See `docs/SESSIONS.md`.
