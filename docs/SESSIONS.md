# Persistent Project Sessions

## Purpose

Persistent Project Session lets multiple interaction channels reuse one agent conversation context without making Telegram, Desktop, or Codex itself the owner of project state.

```text
Telegram / Desktop
        |
        v
Project OS Project Session
        |
        v
Codex thread/session
        |
   Job -> Job -> Job
```

A Project can have many historical Sessions. Each Session can contain many Jobs. At most one Session per Project is active (`idle` or `running`) in the default policy.

## Storage

Session metadata is operational state in the central control DB:

```text
~/.project-os/control.db
  projects
  sessions
  jobs
  runs
  events
  ...
```

Control DB schema version 2 adds `sessions` and `jobs`.

This DB is not copied into consumer repositories and does not replace:

- `PROJECT.md`
- `specs/`
- `.project-os/state/`
- `.project-os/tasks/`
- `.project-os/decisions/`

If the Codex session disappears, Project OS must still be able to rebuild context from the Git-managed project state.

## Session fields

A session stores the operational equivalent of:

```yaml
session_id: S-20260924-AB12CD34
project_id: project-os
codex_session_id: 019f...
status: idle
created_at: ...
last_activity_at: ...
created_by: telegram
worker_id: desktop-home
last_job_id: JOB-...
title: Remote Session
metadata:
  codex_source: exec
locked_by_job_id: null
locked_at: null
```

Statuses:

- `idle`: active and resumable
- `running`: locked by one Job/attach process
- `closed`: historical session after manual rollover
- `error`: runtime session is no longer trusted

## Job lifecycle

A Job is one user request/execution unit.

```text
begin_job
  |
  +-- no active Session -> create lazy Session
  |
  +-- active Session without codex_session_id -> new_session
  |
  +-- active Session with codex_session_id -> resumed_session
  |
  v
lock Session
  |
  v
codex exec / codex exec resume
  |
  v
thread.started -> bind/verify thread_id
  |
  v
finish_job -> unlock Session
```

Job observability includes:

- `project_id`
- `session_id`
- `codex_session_id`
- `job_id`
- `worker_id`
- `source`
- `execution_mode`

Execution mode is one of `new_session`, `resumed_session`, or `attached_session`.

## Codex thread capture

Headless Codex execution uses JSONL output.

The adapter looks for:

```json
{"type":"thread.started","thread_id":"019f..."}
```

For the first Job, that id becomes the Session's `codex_session_id`.

For a resumed Job, the emitted id must equal the requested id.

This equality check is required because Codex versions have existed where a missing/stale resume id can silently start a different thread and exit successfully. Project OS therefore does not treat exit code 0 alone as proof that resume succeeded.

## Codex command construction

The adapter uses argument arrays and `shell=False`.

New session:

```text
codex exec --json -- <prompt>
```

Resume:

```text
codex exec resume <codex_session_id> --json -- <prompt>
```

Interactive Desktop attach:

```text
codex resume --include-non-interactive <codex_session_id>
```

The prompt is never interpolated into a shell command string.

## CODEX_HOME

Remote Worker and Desktop must point at the same Codex local store if they need to resume the same thread.

Resolution order:

1. `PROJECT_OS_CODEX_HOME`
2. `CODEX_HOME`
3. Codex default home

`PROJECT_OS_CODEX_BIN` may be used to pin the executable path when PATH resolution differs between a service account and an interactive shell.

No user-specific path is hard-coded.

## Telegram / messenger integration

Project OS does not own Telegram networking or authorization. A gateway should use the transport-neutral services.

Slash commands:

- `/session` -> `SessionCommandHandler.handle(...)` -> active session
- `/session new` -> close idle active session and create a lazy fresh session
- `/sessions` -> recent sessions for the current Project

Normal message:

```python
executor.execute(
    project_id,
    job_id,
    prompt,
    source="telegram",
    worker_id="desktop-home",
    cwd=project_root,
)
```

`CodexSessionExecutor` performs:

1. active Session resolve,
2. lock acquisition,
3. new vs resume command selection,
4. `thread.started` capture,
5. resume identity verification,
6. one controlled recovery to a new Session when resume is stale/broken,
7. lock release and Job observability update.

The gateway remains responsible for converting the returned result into a Telegram message.

## Desktop CLI

List Sessions:

```bash
projectctl sessions
projectctl sessions --project project-os
```

Show one:

```bash
projectctl session show S-20260924-AB12CD34
```

Create a fresh lazy Session:

```bash
projectctl session new project-os --created-by telegram
```

Attach the Codex TUI to a Session created by headless `exec`:

```bash
projectctl session attach S-20260924-AB12CD34
```

Attach itself is recorded as an `attached_session` Job and holds the same Session lock until the interactive Codex process exits.

## Remote worker integration CLI

A worker that cannot import the Python service can use the CLI contract.

Resolve and lock:

```bash
projectctl session begin-job project-os JOB-123 --source telegram --worker-id desktop-home
```

Persist/verify first JSON event:

```bash
projectctl session bind-thread JOB-123 019f...
```

Finish:

```bash
projectctl session finish-job JOB-123
```

After a detected stale resume:

```bash
projectctl session recover-job JOB-123
```

Direct Python integration is preferred because it avoids additional subprocess boundaries.

## Concurrency and stale locks

One active Project Session can be used by only one running Job/attach at a time.

```text
idle
  -> begin Job
running + locked_by_job_id
  -> finish
idle
```

A second Job receives `SESSION_LOCKED` semantics rather than running the same Codex thread concurrently.

The default stale-lock threshold is two hours. When a running lock is older than that threshold, SessionService marks the abandoned Job as failed with `SESSION_STALE_LOCK_RECOVERED` and returns the Session to `idle`.

Current limitation: stale recovery is age-based. The current control DB does not yet have a cross-host process heartbeat/lease that can prove a worker PID is gone.

## Resume failure recovery

A stale/missing Codex session is handled once, not retried forever.

```text
resume requested
   |
thread.started id mismatch
or resume process failure
   |
old Session -> error
Job -> SESSION_NOT_FOUND / CODEX_RESUME_FAILED
   |
new lazy Session
   |
same Job -> new_session
   |
persistent project state is still available for context recovery
```

The executor retries only once on a new Session.

## Rollover

Manual rollover is supported:

```text
/session new
projectctl session new <project>
```

The previous idle Session becomes `closed`; it is not deleted.

Automatic rollover by estimated token count is intentionally not implemented because Project OS does not have a reliable runtime token-limit signal for the entire Codex thread.

If a project needs a durable checkpoint before rollover, reuse its existing `.project-os/state/current.yaml`, handoff, decision and run-summary mechanisms. Do not create a second canonical checkpoint system inside Session storage.

## Limits

- This repository provides Session persistence, Codex lifecycle execution, slash-command semantics and Desktop attach. The Telegram network bot/authorization code still lives in the separate Remote Control system and must call these APIs.
- `projectctl session attach` depends on the installed Codex CLI supporting direct resume of a non-interactive session id.
- Some Codex Desktop/VS Code UIs may not list `exec` sessions even when direct CLI resume by id works. Project OS therefore treats the stored id, not GUI discoverability, as the integration contract.
- Stale lock recovery currently uses age, not distributed heartbeat.
