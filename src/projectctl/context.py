from __future__ import annotations

from typing import Any

import yaml

from .models import ContextPackage
from .project import Project


class FileContextBuilder:
    def __init__(self, project: Project):
        self.project = project

    def _task(self, task_id: str) -> dict[str, Any]:
        contract = self.project.find_task_contract(task_id)
        if contract is not None:
            return yaml.safe_load(contract.read_text(encoding="utf-8")) or {}

        for task in self.project.backlog().get("tasks", []) or []:
            if task.get("id") == task_id:
                return task

        raise KeyError(f"Unknown task: {task_id}")

    def build(self, task_id: str, role: str | None = None) -> dict[str, Any]:
        task = self._task(task_id)
        if role and task.get("role") and task.get("role") != role:
            raise ValueError(
                f"Task {task_id} is assigned to role {task.get('role')}, not {role}"
            )

        package = ContextPackage(
            task=task,
            project_file="PROJECT.md",
            specs=list(task.get("specs", []) or []),
            relevant_files=list(task.get("relevant_files", []) or []),
            active_decisions=list(task.get("active_decisions", []) or []),
            acceptance=list(task.get("acceptance", []) or []),
            verification=list(task.get("verification", []) or []),
        )
        return package.model_dump()
