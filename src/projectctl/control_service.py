from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .central_store import CentralControlStore
from .project import Project
from .versioning import check_compatibility, parse_version


def default_control_db() -> Path:
    return Path.home() / ".project-os" / "control.db"


class CentralControlService:
    """Observes many Project OS repositories without owning their canonical state."""

    def __init__(self, store: CentralControlStore):
        self.store = store

    def _snapshot(self, root: Path) -> dict[str, Any]:
        project = Project(root.resolve())
        status = project.status()
        manifest_os = project.manifest.get("project_os", {}) or {}
        compatibility = check_compatibility(
            __version__,
            manifest_os.get("package_compatibility"),
        )
        return {
            "project_id": status.project_id,
            "project_name": status.project_name,
            "root_path": project.root.as_posix(),
            "project_status": status.project_status,
            "current_milestone": status.current_milestone,
            "human_gate": status.human_gate,
            "scaffold_version": str(manifest_os.get("scaffold_version", "")),
            "schema_version": str(manifest_os.get("schema_version", "")),
            "package_compatibility": manifest_os.get("package_compatibility"),
            "compatibility_status": "compatible" if compatibility.compatible else "incompatible",
            "compatibility_reason": compatibility.reason,
        }

    def register_project(self, root: Path) -> dict[str, Any]:
        snapshot = self._snapshot(root)
        if not snapshot["project_id"]:
            raise ValueError("Project manifest must declare project.id")
        self.store.upsert_project(snapshot)
        return self.store.get_project(snapshot["project_id"]) or snapshot

    def sync_project(self, project_id: str) -> dict[str, Any]:
        registered = self.store.get_project(project_id)
        if registered is None:
            raise KeyError(f"Unknown registered project: {project_id}")
        snapshot = self._snapshot(Path(registered["root_path"]))
        if snapshot["project_id"] != project_id:
            raise ValueError(
                f"Registered project id {project_id} no longer matches "
                f"repository manifest id {snapshot['project_id']}"
            )
        self.store.upsert_project(snapshot)
        return self.store.get_project(project_id) or snapshot

    def list_projects(self) -> list[dict[str, Any]]:
        return self.store.list_projects()

    def project(self, project_id: str) -> dict[str, Any]:
        record = self.store.get_project(project_id)
        if record is None:
            raise KeyError(f"Unknown registered project: {project_id}")
        return record

    def start_run(
        self,
        project_id: str,
        run_id: str,
        workflow: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.store.upsert_run(
            project_id=project_id,
            run_id=run_id,
            workflow=workflow,
            status="RUNNING",
            metadata=metadata,
        )
        return self.store.get_run(run_id) or {}

    def update_run(
        self,
        run_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.store.get_run(run_id)
        if existing is None:
            raise KeyError(f"Unknown central run: {run_id}")
        merged_metadata = dict(existing.get("metadata", {}) or {})
        if metadata:
            merged_metadata.update(metadata)
        self.store.upsert_run(
            project_id=str(existing["project_id"]),
            run_id=run_id,
            workflow=existing.get("workflow"),
            status=status,
            metadata=merged_metadata,
        )
        return self.store.get_run(run_id) or {}

    def active_runs(self, project_id: str | None = None) -> list[dict[str, Any]]:
        return self.store.list_runs(project_id=project_id, active_only=True)

    def set_model_policy(
        self,
        project_id: str,
        role: str,
        provider: str,
        model: str,
        max_cost: float | None = None,
        currency: str = "USD",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.store.set_model_policy(
            project_id=project_id,
            role=role,
            provider=provider,
            model=model,
            max_cost=max_cost,
            currency=currency,
            config=config,
        )
        return self.store.get_model_policy(project_id, role) or {}

    def record_usage(
        self,
        project_id: str,
        provider: str,
        model: str,
        role: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        currency: str = "USD",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        self.store.record_usage(
            project_id=project_id,
            provider=provider,
            model=model,
            role=role,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            currency=currency,
            run_id=run_id,
        )
        return self.store.usage_summary(project_id, run_id=run_id)

    def model_budget_status(self, project_id: str, role: str) -> dict[str, Any]:
        return self.store.model_budget_status(project_id, role)

    def record_evaluation(
        self,
        project_id: str,
        task_id: str,
        decision: str,
        metrics: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self.store.record_evaluation(
            project_id=project_id,
            task_id=task_id,
            decision=decision,
            metrics=metrics,
            run_id=run_id,
        )
        return self.store.evaluation_history(project_id, task_id)

    def assess_migration(
        self,
        project_id: str,
        target_schema_version: str,
    ) -> dict[str, Any]:
        project = self.project(project_id)
        observed = str(project["schema_version"])
        try:
            observed_version = parse_version(observed)
            target_version = parse_version(target_schema_version)
        except ValueError as exc:
            status = "invalid_version"
            message = str(exc)
        else:
            if observed_version == target_version:
                status = "up_to_date"
                message = f"Project schema {observed} already matches target {target_schema_version}"
            elif observed_version < target_version:
                status = "migration_required"
                message = (
                    f"Project schema {observed} requires an ordered migration "
                    f"to {target_schema_version}"
                )
            else:
                status = "project_ahead"
                message = (
                    f"Project schema {observed} is newer than control target "
                    f"{target_schema_version}"
                )

        self.store.set_migration_status(
            project_id=project_id,
            observed_schema_version=observed,
            target_schema_version=target_schema_version,
            status=status,
            message=message,
        )
        return self.store.get_migration_status(project_id) or {}

    def dashboard(self) -> dict[str, Any]:
        projects = self.list_projects()
        active_runs = self.active_runs()
        return {
            "db_schema_version": self.store.db_schema_version(),
            "projects": projects,
            "active_runs": active_runs,
            "project_count": len(projects),
            "active_run_count": len(active_runs),
        }
