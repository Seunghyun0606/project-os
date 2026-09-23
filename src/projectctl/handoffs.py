from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .project import Project
from .quality import QualityGateEvaluator
from .roles import RolePolicyResolver
from .transitions import CanonicalStateWriter


HANDOFF_SUFFIX = {
    "implementation": "",
    "review": ".review",
    "qa": ".qa",
    "evaluation": ".evaluation",
}

HANDOFF_CAPABILITY = {
    "implementation": "task_result",
    "review": "review_result",
    "qa": "qa_result",
    "evaluation": "evaluation_result",
}


def resolve_actor(explicit: str | None, role: str) -> str:
    value = explicit or os.environ.get("PROJECT_OS_ACTOR") or role
    value = value.strip()
    if not value:
        raise ValueError("Actor identity must not be empty")
    return value


class HandoffStore:
    def __init__(self, project: Project):
        self.project = project
        self.roles = RolePolicyResolver(project)

    def path(self, task_id: str, kind: str) -> Path:
        if kind not in HANDOFF_SUFFIX:
            raise ValueError(f"Unknown handoff kind: {kind}")
        return (
            self.project.root
            / ".project-os"
            / "tasks"
            / "results"
            / f"{task_id}{HANDOFF_SUFFIX[kind]}.yaml"
        )

    def load(self, task_id: str, kind: str) -> dict[str, Any] | None:
        path = self.path(task_id, kind)
        if not path.is_file():
            return None
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid handoff payload: {path}")
        return payload

    def _assert_independent(self, task_id: str, kind: str, actor: str) -> None:
        if kind not in {"review", "qa", "evaluation"}:
            return

        compared = ["implementation"]
        if kind == "evaluation":
            compared.extend(["review", "qa"])

        for previous_kind in compared:
            previous = self.load(task_id, previous_kind)
            if previous is None:
                continue
            previous_actor = previous.get("actor")
            if previous_actor and str(previous_actor) == actor:
                raise PermissionError(
                    f"Actor {actor} cannot submit {kind} for its own {previous_kind} output"
                )

    def submit(
        self,
        task_id: str,
        kind: str,
        payload: dict[str, Any],
        role: str,
        actor: str,
    ) -> Path:
        capability = HANDOFF_CAPABILITY[kind]
        self.roles.require_write(role, capability)
        self._assert_independent(task_id, kind, actor)

        if payload.get("task") not in (None, task_id):
            raise ValueError("Handoff task id does not match command task id")

        normalized = dict(payload)
        normalized["task"] = task_id
        normalized["kind"] = kind
        normalized["role"] = role
        normalized["actor"] = actor

        destination = self.path(task_id, kind)
        destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = yaml.safe_dump(normalized, sort_keys=False, allow_unicode=True)

        if destination.exists():
            existing = destination.read_text(encoding="utf-8")
            if existing == serialized:
                return destination
            raise FileExistsError(
                f"Refusing to overwrite existing handoff: {destination.relative_to(self.project.root)}"
            )

        destination.write_text(serialized, encoding="utf-8")
        return destination


class EvaluationService:
    def __init__(self, project: Project):
        self.project = project
        self.handoffs = HandoffStore(project)
        self.state = CanonicalStateWriter(project)

    def evaluate(
        self,
        task_id: str,
        payload: dict[str, Any],
        actor: str,
    ) -> Path:
        decision = str(payload.get("decision", payload.get("status", ""))).strip().upper()
        if decision not in {"PASS", "REWORK", "HUMAN_GATE"}:
            raise ValueError("Evaluation decision must be PASS, REWORK or HUMAN_GATE")

        implementation = self.handoffs.load(task_id, "implementation")
        if implementation is None:
            raise ValueError(f"Task {task_id} has no implementation result")

        if decision == "PASS":
            quality = QualityGateEvaluator(self.project).check(task_id)
            if not quality["passed"]:
                problems = quality["missing"] + quality["failed"]
                raise ValueError(
                    "PASS is not allowed because configured quality gates are not satisfied: "
                    + ", ".join(problems)
                )

        normalized = dict(payload)
        normalized["decision"] = decision
        normalized["quality"] = QualityGateEvaluator(self.project).check(task_id)
        destination = self.handoffs.submit(
            task_id=task_id,
            kind="evaluation",
            payload=normalized,
            role="evaluator",
            actor=actor,
        )
        self.state.apply_evaluation(task_id, decision)
        return destination
