from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .context import FileContextBuilder
from .handoffs import EvaluationService, HandoffStore, resolve_actor
from .harness_models import HarnessResult
from .project import Project
from .scheduler import DeterministicTaskScheduler
from .transitions import CanonicalStateWriter


class ProjectService:
    """Harness-neutral business API over Project OS deterministic core."""

    def __init__(self, project: Project):
        self.project = project

    @classmethod
    def open(cls, start: Path | None = None) -> "ProjectService":
        return cls(Project.open(start))

    def _call(self, action: str, operation: Callable[[], dict[str, Any]]) -> HarnessResult:
        try:
            return HarnessResult.success(action, operation())
        except KeyError as exc:
            return HarnessResult.failure(action, "not_found", str(exc))
        except PermissionError as exc:
            return HarnessResult.failure(action, "permission_denied", str(exc))
        except FileExistsError as exc:
            return HarnessResult.failure(action, "conflict", str(exc))
        except (ValueError, TypeError) as exc:
            return HarnessResult.failure(action, "invalid_request", str(exc))

    def _task_role(self, task_id: str) -> str:
        for task in self.project.backlog().get("tasks", []) or []:
            if task.get("id") == task_id:
                return str(task.get("role", "developer"))
        raise KeyError(f"Unknown task: {task_id}")

    def get_status(self) -> HarnessResult:
        return self._call(
            "get_status",
            lambda: self.project.status().model_dump(),
        )

    def get_next_task(self, role: str = "developer") -> HarnessResult:
        def operation() -> dict[str, Any]:
            task = DeterministicTaskScheduler(self.project).next_task(role)
            return {"task": task}

        return self._call("get_next_task", operation)

    def build_context(
        self,
        task_id: str,
        role: str | None = None,
    ) -> HarnessResult:
        return self._call(
            "build_context",
            lambda: FileContextBuilder(self.project).build(task_id, role),
        )

    def claim_task(self, task_id: str, role: str = "developer") -> HarnessResult:
        def operation() -> dict[str, Any]:
            CanonicalStateWriter(self.project).claim(task_id, role)
            return {"task_id": task_id, "status": "active", "role": role}

        return self._call("claim_task", operation)

    def submit_result(
        self,
        task_id: str,
        payload: dict[str, Any],
        role: str | None = None,
        actor: str | None = None,
    ) -> HarnessResult:
        def operation() -> dict[str, Any]:
            resolved_role = role or self._task_role(task_id)
            resolved_actor = resolve_actor(actor, resolved_role)
            destination = HandoffStore(self.project).submit(
                task_id=task_id,
                kind="implementation",
                payload=payload,
                role=resolved_role,
                actor=resolved_actor,
            )
            return {
                "task_id": task_id,
                "kind": "implementation",
                "role": resolved_role,
                "actor": resolved_actor,
                "path": destination.relative_to(self.project.root).as_posix(),
            }

        return self._call("submit_result", operation)

    def submit_review(
        self,
        task_id: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> HarnessResult:
        def operation() -> dict[str, Any]:
            resolved_actor = resolve_actor(actor, "reviewer")
            destination = HandoffStore(self.project).submit(
                task_id=task_id,
                kind="review",
                payload=payload,
                role="reviewer",
                actor=resolved_actor,
            )
            return {
                "task_id": task_id,
                "kind": "review",
                "role": "reviewer",
                "actor": resolved_actor,
                "path": destination.relative_to(self.project.root).as_posix(),
            }

        return self._call("submit_review", operation)

    def submit_qa(
        self,
        task_id: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> HarnessResult:
        def operation() -> dict[str, Any]:
            resolved_actor = resolve_actor(actor, "qa")
            destination = HandoffStore(self.project).submit(
                task_id=task_id,
                kind="qa",
                payload=payload,
                role="qa",
                actor=resolved_actor,
            )
            return {
                "task_id": task_id,
                "kind": "qa",
                "role": "qa",
                "actor": resolved_actor,
                "path": destination.relative_to(self.project.root).as_posix(),
            }

        return self._call("submit_qa", operation)

    def record_test_result(
        self,
        task_id: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> HarnessResult:
        def operation() -> dict[str, Any]:
            resolved_actor = resolve_actor(actor, "qa")
            destination = HandoffStore(self.project).submit(
                task_id=task_id,
                kind="test",
                payload=payload,
                role="qa",
                actor=resolved_actor,
            )
            return {
                "task_id": task_id,
                "kind": "test",
                "role": "qa",
                "actor": resolved_actor,
                "path": destination.relative_to(self.project.root).as_posix(),
            }

        return self._call("record_test_result", operation)

    def evaluate_task(
        self,
        task_id: str,
        payload: dict[str, Any],
        actor: str | None = None,
    ) -> HarnessResult:
        def operation() -> dict[str, Any]:
            resolved_actor = resolve_actor(actor, "evaluator")
            destination = EvaluationService(self.project).evaluate(
                task_id=task_id,
                payload=payload,
                actor=resolved_actor,
            )
            decision = str(
                payload.get("decision", payload.get("status", ""))
            ).strip().upper()
            return {
                "task_id": task_id,
                "decision": decision,
                "actor": resolved_actor,
                "path": destination.relative_to(self.project.root).as_posix(),
            }

        return self._call("evaluate_task", operation)
