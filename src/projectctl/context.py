from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .interfaces import CodeMapAdapter
from .models import ContextPackage, ContextResource
from .project import Project


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _estimate_tokens(value: Any) -> int:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, (len(serialized) + 3) // 4)


class FileContextBuilder:
    def __init__(self, project: Project, code_map: CodeMapAdapter | None = None):
        self.project = project
        self.code_map = code_map

    def _task(self, task_id: str) -> dict[str, Any]:
        contract = self.project.find_task_contract(task_id)
        if contract is not None:
            return yaml.safe_load(contract.read_text(encoding="utf-8")) or {}

        for task in self.project.backlog().get("tasks", []) or []:
            if task.get("id") == task_id:
                return task

        raise KeyError(f"Unknown task: {task_id}")

    def _default_context_policies(self) -> dict[str, Any]:
        packaged = files("projectctl").joinpath("_defaults", "context", "default.yaml")
        if packaged.is_file():
            return yaml.safe_load(packaged.read_text(encoding="utf-8")) or {}

        development = Path(__file__).resolve().parents[2] / "defaults" / "context" / "default.yaml"
        if development.is_file():
            return yaml.safe_load(development.read_text(encoding="utf-8")) or {}

        return {}

    def _policy(self, role: str) -> dict[str, Any]:
        defaults = self._default_context_policies().get(role, {})
        profile = self.project.store.load_yaml("profile.yaml")
        overrides = profile.get("overrides", {}) or {}
        role_override = ((overrides.get("context", {}) or {}).get(role, {}) or {})
        return _deep_merge(defaults, role_override)

    def _safe_file(self, relative: str, kind: str) -> ContextResource | None:
        candidate = (self.project.root / relative).resolve()
        root = self.project.root.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return ContextResource(
            kind=kind,
            path=candidate.relative_to(root).as_posix(),
            content=candidate.read_text(encoding="utf-8"),
        )

    def _context_index_paths(self, task: dict[str, Any]) -> list[str]:
        index = self.project.store.load_yaml("context/index.yaml")
        domains = index.get("domains", {}) or {}
        paths: list[str] = []
        for key in sorted(task.get("context_keys", []) or []):
            entry = domains.get(key)
            if isinstance(entry, str):
                paths.append(entry)
            elif isinstance(entry, list):
                paths.extend(str(item) for item in entry)
            elif isinstance(entry, dict):
                values = entry.get("paths", []) or []
                if isinstance(values, str):
                    paths.append(values)
                else:
                    paths.extend(str(item) for item in values)
        return paths

    def _active_decision_paths(self, task: dict[str, Any]) -> list[str]:
        explicit = [str(item) for item in task.get("active_decisions", []) or []]
        found: list[str] = []
        decisions_root = self.project.root / ".project-os" / "decisions"
        if decisions_root.is_dir():
            for path in sorted(decisions_root.glob("*.yaml")):
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if str(data.get("status", "")).lower() != "active":
                    continue
                applies_to = data.get("applies_to", []) or []
                if isinstance(applies_to, str):
                    applies_to = [applies_to]
                if not applies_to or "global" in applies_to or task.get("id") in applies_to:
                    found.append(path.relative_to(self.project.root).as_posix())
        return sorted(set(explicit + found))

    def _dependency_results(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for dependency in sorted(task.get("depends_on", []) or []):
            path = self.project.root / ".project-os" / "tasks" / "results" / f"{dependency}.yaml"
            if not path.is_file():
                continue
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            summaries.append({
                "task": dependency,
                "status": payload.get("status"),
                "summary": payload.get("summary"),
                "artifacts": list(payload.get("artifacts", []) or []),
            })
        return summaries

    def _candidate_resources(
        self,
        task: dict[str, Any],
        policy: dict[str, Any],
        decision_paths: list[str],
    ) -> list[ContextResource]:
        include = set(policy.get("include", []) or [])
        candidates: list[ContextResource] = []

        def add(path: str, kind: str) -> None:
            resource = self._safe_file(path, kind)
            if resource is not None and all(existing.path != resource.path for existing in candidates):
                candidates.append(resource)

        if "project" in include:
            add("PROJECT.md", "project")
        if "state" in include:
            add(".project-os/state/current.yaml", "state")
        if "roadmap" in include:
            add(".project-os/state/roadmap.yaml", "roadmap")
        if "current_milestone" in include:
            current = self.project.current_state().get("current_milestone")
            if current:
                add(f".project-os/milestones/{current}.yaml", "milestone")
        if "relevant_specs" in include:
            for path in sorted(task.get("specs", []) or []):
                add(str(path), "spec")
        if "relevant_files" in include or "relevant_code" in include:
            for path in sorted(task.get("relevant_files", []) or []):
                add(str(path), "relevant_file")
        if "active_decisions" in include:
            for path in decision_paths:
                add(path, "decision")

        for path in self._context_index_paths(task):
            add(path, "context_index")

        if self.code_map is not None and task.get("symbols"):
            mapped = self.code_map.lookup([str(item) for item in task.get("symbols", [])])
            candidates.append(ContextResource(
                kind="code_map",
                path="<adapter>",
                content=json.dumps(mapped, ensure_ascii=False, indent=2),
            ))

        return candidates

    def _fit_resources(
        self,
        base_payload: dict[str, Any],
        resources: list[ContextResource],
        budget: int,
    ) -> tuple[list[ContextResource], int, bool]:
        selected: list[ContextResource] = []
        used = _estimate_tokens(base_payload)
        truncated = False

        for resource in resources:
            resource_tokens = _estimate_tokens(resource.model_dump())
            if used + resource_tokens <= budget:
                selected.append(resource)
                used += resource_tokens
                continue

            remaining = max(0, budget - used)
            if remaining >= 32:
                max_chars = remaining * 4
                selected.append(ContextResource(
                    kind=resource.kind,
                    path=resource.path,
                    content=resource.content[:max_chars],
                ))
                used = budget
            truncated = True
            break

        if len(selected) < len(resources):
            truncated = True
        return selected, used, truncated

    def build(self, task_id: str, role: str | None = None) -> dict[str, Any]:
        task = self._task(task_id)
        resolved_role = role or str(task.get("role", "developer"))
        if task.get("role") and task.get("role") != resolved_role:
            raise ValueError(
                f"Task {task_id} is assigned to role {task.get('role')}, not {resolved_role}"
            )

        policy = self._policy(resolved_role)
        budget = int(policy.get("target_tokens", 8000))
        if budget <= 0:
            raise ValueError(f"Context token budget must be positive for role {resolved_role}")

        decisions = self._active_decision_paths(task)
        results = self._dependency_results(task)
        base = {
            "task": task,
            "role": resolved_role,
            "policy": policy,
            "active_decisions": decisions,
            "task_results": results,
            "acceptance": list(task.get("acceptance", []) or []),
            "verification": list(task.get("verification", []) or []),
            "token_budget": budget,
        }
        resources = self._candidate_resources(task, policy, decisions)
        selected, estimated, truncated = self._fit_resources(base, resources, budget)

        package = ContextPackage(
            **base,
            project_file="PROJECT.md",
            specs=list(task.get("specs", []) or []),
            relevant_files=list(task.get("relevant_files", []) or []),
            resources=selected,
            estimated_tokens=estimated,
            truncated=truncated,
        )
        return package.model_dump()
