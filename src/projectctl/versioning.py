from __future__ import annotations

import re
from dataclasses import dataclass


_VERSION_RE = re.compile(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*$")
_SPEC_RE = re.compile(r"^\s*(>=|<=|==|>|<)\s*(\d+(?:\.\d+){0,2})\s*$")


def parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_RE.match(value)
    if not match:
        raise ValueError(f"Unsupported version: {value}")
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


@dataclass(frozen=True)
class CompatibilityResult:
    compatible: bool
    reason: str


def check_compatibility(version: str, specification: str | None) -> CompatibilityResult:
    if not specification:
        return CompatibilityResult(True, "No package compatibility constraint declared")

    current = parse_version(version)
    for clause in specification.split(","):
        match = _SPEC_RE.match(clause)
        if not match:
            return CompatibilityResult(False, f"Unsupported compatibility clause: {clause.strip()}")
        operator, expected_text = match.groups()
        expected = parse_version(expected_text)
        ok = {
            ">=": current >= expected,
            "<=": current <= expected,
            ">": current > expected,
            "<": current < expected,
            "==": current == expected,
        }[operator]
        if not ok:
            return CompatibilityResult(
                False,
                f"projectctl {version} does not satisfy {clause.strip()}",
            )
    return CompatibilityResult(True, f"projectctl {version} satisfies {specification}")
