from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .project import Project


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


class RolePolicyResolver:
    def __init__(self, project: Project):
        self.project = project

    def _default_path(self, role: str):
        packaged = files("projectctl").joinpath("_defaults", "roles", f"{role}.yaml")
        if packaged.is_file():
            return packaged
        development = Path(__file__).resolve().parents[2] / "defaults" / "roles" / f"{role}.yaml"
        if development.is_file():
            return development
        raise KeyError(f"Unknown role: {role}")

    def resolve(self, role: str) -> dict[str, Any]:
        source = self._default_path(role)
        base = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        profile = self.project.store.load_yaml("profile.yaml")
        overrides = profile.get("overrides", {}) or {}
        role_override = ((overrides.get("roles", {}) or {}).get(role, {}) or {})
        resolved = _deep_merge(base, role_override)
        resolved["role"] = role
        return resolved

    def can_write(self, role: str, capability: str) -> bool:
        policy = self.resolve(role)
        return capability in set(policy.get("writes", []) or [])

    def require_write(self, role: str, capability: str) -> None:
        if not self.can_write(role, capability):
            raise PermissionError(
                f"Role {role} is not allowed to write capability {capability}"
            )
