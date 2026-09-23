from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


CONTROL_DB_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: str | None, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value)


class CentralControlStore:
    """SQLite runtime/observability store. Never owns canonical project planning state."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", timeout=30)
            self._memory_connection.row_factory = sqlite3.Row
            self._memory_connection.execute("PRAGMA foreign_keys = ON")
            self._memory_connection.execute("PRAGMA busy_timeout = 30000")
        else:
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.path = str(Path(self.path).expanduser().resolve())
        self._migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        owned = self._memory_connection is None
        connection = self._memory_connection or sqlite3.connect(self.path, timeout=30)
        if owned:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 30000")
            connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            if owned:
                connection.close()

    def _migrate(self) -> None:
        with self.connect() as connection:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current > CONTROL_DB_SCHEMA_VERSION:
                raise RuntimeError(
                    f"Control DB schema {current} is newer than supported "
                    f"{CONTROL_DB_SCHEMA_VERSION}"
                )
            if current == 0:
                self._create_schema_v1(connection)
                connection.execute(f"PRAGMA user_version = {CONTROL_DB_SCHEMA_VERSION}")
                return
            if current != CONTROL_DB_SCHEMA_VERSION:
                raise RuntimeError(
                    f"No ordered control DB migration from {current} to "
                    f"{CONTROL_DB_SCHEMA_VERSION}"
                )

    def _create_schema_v1(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE projects (
                project_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                root_path TEXT NOT NULL UNIQUE,
                project_status TEXT NOT NULL,
                current_milestone TEXT,
                human_gate INTEGER NOT NULL DEFAULT 0,
                scaffold_version TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                package_compatibility TEXT,
                compatibility_status TEXT NOT NULL,
                compatibility_reason TEXT NOT NULL,
                synced_at TEXT NOT NULL
            );

            CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                workflow TEXT,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                project_id TEXT,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );

            CREATE INDEX idx_events_run_id ON events(run_id, id);
            CREATE INDEX idx_events_project_id ON events(project_id, id);

            CREATE TABLE checkpoints (
                run_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE approvals (
                approval_id TEXT PRIMARY KEY,
                gate TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE model_policies (
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                max_cost REAL,
                currency TEXT NOT NULL DEFAULT 'USD',
                config_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                PRIMARY KEY(project_id, role),
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE TABLE usage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                run_id TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE INDEX idx_usage_project_id ON usage_records(project_id, id);
            CREATE INDEX idx_usage_run_id ON usage_records(run_id, id);

            CREATE TABLE evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                run_id TEXT,
                decision TEXT NOT NULL,
                metrics_json TEXT NOT NULL DEFAULT '{}',
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );

            CREATE INDEX idx_eval_project_id ON evaluations(project_id, id);
            CREATE INDEX idx_eval_task_id ON evaluations(project_id, task_id, id);

            CREATE TABLE migration_status (
                project_id TEXT PRIMARY KEY,
                observed_schema_version TEXT NOT NULL,
                target_schema_version TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(project_id)
            );
            """
        )

    def db_schema_version(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("PRAGMA user_version").fetchone()[0])

    def upsert_project(self, record: dict[str, Any]) -> None:
        root_path = str(Path(str(record["root_path"])).resolve())
        with self.connect() as connection:
            conflict = connection.execute(
                "SELECT project_id FROM projects WHERE root_path = ? AND project_id <> ?",
                (root_path, str(record["project_id"])),
            ).fetchone()
            if conflict:
                raise ValueError(
                    f"Repository path is already registered as project {conflict['project_id']}"
                )
            connection.execute(
                """
                INSERT INTO projects (
                    project_id, project_name, root_path, project_status,
                    current_milestone, human_gate, scaffold_version,
                    schema_version, package_compatibility,
                    compatibility_status, compatibility_reason, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    project_name = excluded.project_name,
                    root_path = excluded.root_path,
                    project_status = excluded.project_status,
                    current_milestone = excluded.current_milestone,
                    human_gate = excluded.human_gate,
                    scaffold_version = excluded.scaffold_version,
                    schema_version = excluded.schema_version,
                    package_compatibility = excluded.package_compatibility,
                    compatibility_status = excluded.compatibility_status,
                    compatibility_reason = excluded.compatibility_reason,
                    synced_at = excluded.synced_at
                """,
                (
                    str(record["project_id"]),
                    str(record["project_name"]),
                    root_path,
                    str(record["project_status"]),
                    record.get("current_milestone"),
                    1 if bool(record.get("human_gate", False)) else 0,
                    str(record.get("scaffold_version", "")),
                    str(record.get("schema_version", "")),
                    record.get("package_compatibility"),
                    str(record.get("compatibility_status", "unknown")),
                    str(record.get("compatibility_reason", "")),
                    str(record.get("synced_at") or _now()),
                ),
            )

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["human_gate"] = bool(result["human_gate"])
        return result

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM projects ORDER BY project_id"
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["human_gate"] = bool(item["human_gate"])
            results.append(item)
        return results

    def upsert_run(
        self,
        project_id: str,
        run_id: str,
        status: str,
        workflow: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        with self.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown registered project: {project_id}")
            connection.execute(
                """
                INSERT INTO runs (
                    run_id, project_id, workflow, status, metadata_json,
                    started_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    project_id = excluded.project_id,
                    workflow = COALESCE(excluded.workflow, runs.workflow),
                    status = excluded.status,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    run_id,
                    project_id,
                    workflow,
                    status,
                    _json(metadata or {}),
                    now,
                    now,
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["metadata"] = _decode(result.pop("metadata_json"), {})
        return result

    def list_runs(
        self,
        project_id: str | None = None,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            args.append(project_id)
        if active_only:
            clauses.append("status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED')")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs" + where + " ORDER BY updated_at DESC, run_id",
                tuple(args),
            ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = _decode(item.pop("metadata_json"), {})
            results.append(item)
        return results

    def append_event(self, event: dict[str, Any]) -> None:
        run_id = str(event.get("run_id", "")).strip()
        if not run_id:
            raise ValueError("Central event requires run_id")
        project_id = event.get("project_id")
        event_type = str(event.get("type", "unknown"))
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO events (
                    run_id, project_id, event_type, payload_json, recorded_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, project_id, event_type, _json(event), _now()),
            )

    def read_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM events WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [_decode(row["payload_json"], {}) for row in rows]

    def save_checkpoint(self, run_id: str, state: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO checkpoints (run_id, state_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (run_id, _json(state), _now()),
            )

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM checkpoints WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return None if row is None else _decode(row["state_json"], {})

    def request_approval(self, gate: str, payload: dict[str, Any]) -> str:
        canonical = _json({"gate": gate, "payload": payload})
        approval_id = "approval-" + hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()[:20]
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT gate, payload_json FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if existing:
                if existing["gate"] != gate or _decode(existing["payload_json"], {}) != payload:
                    raise ValueError(f"Approval id collision: {approval_id}")
                return approval_id
            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id, gate, status, payload_json, updated_at
                ) VALUES (?, ?, 'pending', ?, ?)
                """,
                (approval_id, gate, _json(payload), _now()),
            )
        return approval_id

    def approval_status(self, approval_id: str) -> str:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown approval: {approval_id}")
        return str(row["status"])

    def resolve_approval(self, approval_id: str, status: str) -> None:
        normalized = status.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError("Approval resolution must be approved or rejected")
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown approval: {approval_id}")
            current = str(row["status"])
            if current in {"approved", "rejected"} and current != normalized:
                raise ValueError(
                    f"Approval {approval_id} is already resolved as {current}"
                )
            connection.execute(
                "UPDATE approvals SET status = ?, updated_at = ? WHERE approval_id = ?",
                (normalized, _now(), approval_id),
            )

    def set_model_policy(
        self,
        project_id: str,
        role: str,
        provider: str,
        model: str,
        max_cost: float | None = None,
        currency: str = "USD",
        config: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown registered project: {project_id}")
            connection.execute(
                """
                INSERT INTO model_policies (
                    project_id, role, provider, model, max_cost,
                    currency, config_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, role) DO UPDATE SET
                    provider = excluded.provider,
                    model = excluded.model,
                    max_cost = excluded.max_cost,
                    currency = excluded.currency,
                    config_json = excluded.config_json,
                    updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    role,
                    provider,
                    model,
                    max_cost,
                    currency,
                    _json(config or {}),
                    _now(),
                ),
            )

    def get_model_policy(self, project_id: str, role: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM model_policies
                WHERE project_id = ? AND role = ?
                """,
                (project_id, role),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["config"] = _decode(result.pop("config_json"), {})
        return result

    def record_usage(
        self,
        project_id: str,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        currency: str = "USD",
        run_id: str | None = None,
    ) -> None:
        if input_tokens < 0 or output_tokens < 0 or cost < 0:
            raise ValueError("Usage values must be zero or greater")
        with self.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown registered project: {project_id}")
            connection.execute(
                """
                INSERT INTO usage_records (
                    project_id, run_id, provider, model,
                    input_tokens, output_tokens, cost, currency, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    run_id,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    cost,
                    currency,
                    _now(),
                ),
            )

    def usage_summary(
        self,
        project_id: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        clauses = ["project_id = ?"]
        args: list[Any] = [project_id]
        if run_id:
            clauses.append("run_id = ?")
            args.append(run_id)
        where = " AND ".join(clauses)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT provider, model, currency,
                       SUM(input_tokens) AS input_tokens,
                       SUM(output_tokens) AS output_tokens,
                       SUM(cost) AS cost
                FROM usage_records
                WHERE {where}
                GROUP BY provider, model, currency
                ORDER BY provider, model, currency
                """,
                tuple(args),
            ).fetchall()
        groups = [
            {
                "provider": row["provider"],
                "model": row["model"],
                "currency": row["currency"],
                "input_tokens": int(row["input_tokens"] or 0),
                "output_tokens": int(row["output_tokens"] or 0),
                "cost": float(row["cost"] or 0),
            }
            for row in rows
        ]
        return {
            "project_id": project_id,
            "run_id": run_id,
            "groups": groups,
            "input_tokens": sum(item["input_tokens"] for item in groups),
            "output_tokens": sum(item["output_tokens"] for item in groups),
            "cost_by_currency": {
                currency: sum(
                    item["cost"] for item in groups if item["currency"] == currency
                )
                for currency in sorted({item["currency"] for item in groups})
            },
        }

    def record_evaluation(
        self,
        project_id: str,
        task_id: str,
        decision: str,
        metrics: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> None:
        with self.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?",
                (project_id,),
            ).fetchone() is None:
                raise KeyError(f"Unknown registered project: {project_id}")
            connection.execute(
                """
                INSERT INTO evaluations (
                    project_id, task_id, run_id, decision,
                    metrics_json, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    task_id,
                    run_id,
                    decision,
                    _json(metrics or {}),
                    _now(),
                ),
            )

    def evaluation_history(
        self,
        project_id: str,
        task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["project_id = ?"]
        args: list[Any] = [project_id]
        if task_id:
            clauses.append("task_id = ?")
            args.append(task_id)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM evaluations
                WHERE {' AND '.join(clauses)}
                ORDER BY id
                """,
                tuple(args),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["metrics"] = _decode(item.pop("metrics_json"), {})
            results.append(item)
        return results

    def set_migration_status(
        self,
        project_id: str,
        observed_schema_version: str,
        target_schema_version: str,
        status: str,
        message: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO migration_status (
                    project_id, observed_schema_version, target_schema_version,
                    status, message, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    observed_schema_version = excluded.observed_schema_version,
                    target_schema_version = excluded.target_schema_version,
                    status = excluded.status,
                    message = excluded.message,
                    updated_at = excluded.updated_at
                """,
                (
                    project_id,
                    observed_schema_version,
                    target_schema_version,
                    status,
                    message,
                    _now(),
                ),
            )

    def get_migration_status(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM migration_status WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        return None if row is None else dict(row)
