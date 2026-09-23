from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import ProjectStatus
from .storage import YamlProjectStore


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".project-os" / "manifest.yaml").exists():
            return candidate
    raise RuntimeError("Project OS manifest not found. Run projectctl init at the project root.")


class Project:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.store = YamlProjectStore(self.root)
        self.manifest = self.store.load_yaml("manifest.yaml")

    @classmethod
    def open(cls, start: Path | None = None) -> "Project":
        return cls(find_project_root(start))

    def current_state(self) -> dict[str, Any]:
        return self.store.load_yaml("state/current.yaml")

    def backlog(self) -> dict[str, Any]:
        return self.store.load_yaml("state/backlog.yaml")

    def status(self) -> ProjectStatus:
        project = self.manifest.get("project", {})
        state = self.current_state()
        return ProjectStatus(
            project_id=str(project.get("id", "")),
            project_name=str(project.get("name", "")),
            project_status=str(state.get("project_status", "unknown")),
            current_milestone=state.get("current_milestone"),
            current_tasks=list(state.get("current_tasks", []) or []),
            blocked_tasks=list(state.get("blocked_tasks", []) or []),
            human_gate=bool(state.get("human_gate", False)),
        )

    def find_task_contract(self, task_id: str) -> Path | None:
        tasks_root = self.root / ".project-os" / "tasks"
        if not tasks_root.exists():
            return None
        for path in tasks_root.rglob("*.yaml"):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            if data.get("id") == task_id:
                return path
        return None
