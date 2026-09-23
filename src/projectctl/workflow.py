from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    role: str
    task: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    approval_gate: str | None = None


@dataclass(frozen=True)
class WorkflowDefinition:
    id: str
    steps: tuple[WorkflowStep, ...]


class FileWorkflowRegistry:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def _resolve(self, workflow: str) -> Path:
        candidate = Path(workflow)
        if candidate.suffix.lower() in {".yaml", ".yml"} or "/" in workflow or "\\" in workflow:
            path = (self.project_root / candidate).resolve()
        else:
            path = (
                self.project_root
                / ".project-os"
                / "workflows"
                / f"{workflow}.yaml"
            ).resolve()

        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("Workflow path must stay inside the project root") from exc
        return path

    def load(self, workflow: str) -> WorkflowDefinition:
        path = self._resolve(workflow)
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Workflow must contain a mapping: {path}")

        workflow_id = str(payload.get("id", "")).strip()
        if not workflow_id:
            raise ValueError(f"Workflow is missing id: {path}")

        raw_steps = payload.get("steps", []) or []
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError(f"Workflow must contain at least one step: {path}")

        steps: list[WorkflowStep] = []
        seen: set[str] = set()
        for raw in raw_steps:
            if not isinstance(raw, dict):
                raise ValueError(f"Workflow step must be a mapping: {path}")
            step_id = str(raw.get("id", "")).strip()
            role = str(raw.get("role", "")).strip()
            if not step_id or not role:
                raise ValueError(f"Workflow step requires id and role: {path}")
            if step_id in seen:
                raise ValueError(f"Duplicate workflow step id: {step_id}")
            seen.add(step_id)

            task = raw.get("task", {}) or {}
            context = raw.get("context", {}) or {}
            if not isinstance(task, dict) or not isinstance(context, dict):
                raise ValueError(
                    f"Workflow step task/context must be mappings: {step_id}"
                )
            approval = raw.get("approval_gate")
            steps.append(
                WorkflowStep(
                    id=step_id,
                    role=role,
                    task=task,
                    context=context,
                    approval_gate=str(approval).strip() if approval else None,
                )
            )

        return WorkflowDefinition(id=workflow_id, steps=tuple(steps))
