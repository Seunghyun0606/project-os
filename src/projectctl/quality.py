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


def _passed(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"pass", "passed", "success", "ok", "true"}
    if isinstance(value, dict):
        return _passed(value.get("status"))
    return False


class QualityPolicyResolver:
    def __init__(self, project: Project):
        self.project = project

    def _default_quality(self, profile_name: str) -> dict[str, Any]:
        packaged = files("projectctl").joinpath("_defaults", "quality", f"{profile_name}.yaml")
        if packaged.is_file():
            return yaml.safe_load(packaged.read_text(encoding="utf-8")) or {}
        development = Path(__file__).resolve().parents[2] / "defaults" / "quality" / f"{profile_name}.yaml"
        if development.is_file():
            return yaml.safe_load(development.read_text(encoding="utf-8")) or {}
        raise KeyError(f"Unknown quality profile: {profile_name}")

    def resolve(self) -> dict[str, Any]:
        profile = self.project.store.load_yaml("profile.yaml")
        profile_name = str(profile.get("quality_profile", "standard"))
        defaults = self._default_quality(profile_name)
        project_gates = self.project.store.load_yaml("quality/gates.yaml")
        override = ((profile.get("overrides", {}) or {}).get("quality", {}) or {})
        return _deep_merge(_deep_merge(defaults, project_gates), override)


class QualityGateEvaluator:
    AUTOMATED_GATES = ("build", "lint", "typecheck", "unit_test", "integration_test")

    def __init__(self, project: Project):
        self.project = project
        self.policy = QualityPolicyResolver(project).resolve()

    def _result(self, task_id: str, suffix: str = "") -> dict[str, Any] | None:
        path = (
            self.project.root
            / ".project-os"
            / "tasks"
            / "results"
            / f"{task_id}{suffix}.yaml"
        )
        if not path.is_file():
            return None
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return payload if isinstance(payload, dict) else None

    def check(self, task_id: str) -> dict[str, Any]:
        required = self.policy.get("required", {}) or {}
        thresholds = self.policy.get("thresholds", {}) or {}
        implementation = self._result(task_id)
        review = self._result(task_id, ".review")
        qa = self._result(task_id, ".qa")
        tests = self._result(task_id, ".tests")

        missing: list[str] = []
        failed: list[str] = []

        if implementation is None:
            missing.append("implementation_result")
            return {"passed": False, "missing": missing, "failed": failed}

        implementation_verification = implementation.get("verification", {}) or {}
        test_verification = (tests or {}).get("verification", {}) or {}
        verification = dict(implementation_verification)
        verification.update(test_verification)
        for gate in self.AUTOMATED_GATES:
            if bool(required.get(gate, False)) and not _passed(verification.get(gate)):
                failed.append(gate)

        if bool(required.get("acceptance_evidence", False)):
            evidence = list(implementation.get("evidence", []) or [])
            if not evidence and not _passed(verification.get("acceptance")):
                missing.append("acceptance_evidence")

        if bool(required.get("independent_review", False)):
            if review is None:
                missing.append("independent_review")
            elif not _passed(review.get("status", review.get("verdict"))):
                failed.append("independent_review")

        if bool(required.get("qa", False)):
            if qa is None:
                missing.append("qa")
            elif not _passed(qa.get("status", qa.get("verdict"))):
                failed.append("qa")

        max_critical = int(thresholds.get("critical_issues", 0))
        for label, payload in (("review", review), ("qa", qa)):
            if payload is None:
                continue
            critical = int(payload.get("critical_issues", 0) or 0)
            if critical > max_critical:
                failed.append(f"{label}.critical_issues")

        return {
            "passed": not missing and not failed,
            "missing": sorted(set(missing)),
            "failed": sorted(set(failed)),
        }
