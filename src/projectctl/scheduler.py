from __future__ import annotations

from typing import Any

from .project import Project


_PRIORITY = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _priority(task: dict[str, Any]) -> tuple[int, str]:
    value = str(task.get("priority", "P2")).upper()
    return (_PRIORITY.get(value, 99), str(task.get("id", "")))


class DeterministicTaskScheduler:
    def __init__(self, project: Project):
        self.project = project

    def next_task(self, role: str) -> dict[str, Any] | None:
        tasks = list(self.project.backlog().get("tasks", []) or [])
        by_id = {str(task.get("id")): task for task in tasks if task.get("id")}

        def dependency_done(task_id: str) -> bool:
            dep = by_id.get(task_id)
            return bool(dep and dep.get("status") == "done")

        candidates: list[dict[str, Any]] = []
        for task in tasks:
            if task.get("status") != "ready":
                continue
            if task.get("role", "developer") != role:
                continue
            if bool(task.get("human_gate", False)):
                continue
            dependencies = list(task.get("depends_on", []) or [])
            if not all(dependency_done(dep) for dep in dependencies):
                continue
            candidates.append(task)

        if not candidates:
            return None
        return sorted(candidates, key=_priority)[0]
