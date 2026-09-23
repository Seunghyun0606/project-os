from __future__ import annotations

from typing import Any

from .project import Project
from .scheduler import DeterministicTaskScheduler


class CanonicalStateWriter:
    """The only application service allowed to mutate canonical task/current state."""

    def __init__(self, project: Project):
        self.project = project

    def _task(self, backlog: dict[str, Any], task_id: str) -> dict[str, Any]:
        for task in backlog.get("tasks", []) or []:
            if task.get("id") == task_id:
                return task
        raise KeyError(f"Unknown task: {task_id}")

    def claim(self, task_id: str, role: str) -> None:
        selected = DeterministicTaskScheduler(self.project).next_task(role)
        if selected is None or selected.get("id") != task_id:
            raise ValueError(f"{task_id} is not the next eligible task for role {role}")

        backlog = self.project.backlog()
        task = self._task(backlog, task_id)
        task["status"] = "active"

        state = self.project.current_state()
        current = list(state.get("current_tasks", []) or [])
        if task_id not in current:
            current.append(task_id)
        state["current_tasks"] = current
        blocked = list(state.get("blocked_tasks", []) or [])
        state["blocked_tasks"] = [item for item in blocked if item != task_id]

        self.project.store.save_yaml("state/backlog.yaml", backlog)
        self.project.store.save_yaml("state/current.yaml", state)

    def apply_evaluation(self, task_id: str, decision: str) -> None:
        normalized = decision.strip().upper()
        if normalized not in {"PASS", "REWORK", "HUMAN_GATE"}:
            raise ValueError(f"Unsupported evaluation decision: {decision}")

        backlog = self.project.backlog()
        task = self._task(backlog, task_id)
        state = self.project.current_state()

        current = [item for item in list(state.get("current_tasks", []) or []) if item != task_id]
        blocked = [item for item in list(state.get("blocked_tasks", []) or []) if item != task_id]

        if normalized == "PASS":
            task["status"] = "done"
            task["human_gate"] = False
        elif normalized == "REWORK":
            task["status"] = "ready"
            task["human_gate"] = False
        else:
            task["status"] = "blocked"
            task["human_gate"] = True
            blocked.append(task_id)

        state["current_tasks"] = current
        state["blocked_tasks"] = sorted(set(blocked))
        state["human_gate"] = bool(state["blocked_tasks"])

        self.project.store.save_yaml("state/backlog.yaml", backlog)
        self.project.store.save_yaml("state/current.yaml", state)
