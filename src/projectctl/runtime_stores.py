from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_id(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or not _SAFE_ID.fullmatch(normalized):
        raise ValueError(f"{label} must contain only letters, numbers, dot, underscore or hyphen")
    return normalized


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    temporary.replace(path)


class FileCheckpointStore:
    def __init__(self, project_root: Path):
        self.root = project_root.resolve() / ".project-os" / "runs" / "runtime" / "checkpoints"

    def _path(self, run_id: str) -> Path:
        return self.root / f"{_safe_id(run_id, 'run_id')}.yaml"

    def save_checkpoint(self, run_id: str, state: dict[str, Any]) -> None:
        _atomic_yaml(self._path(run_id), state)

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        path = self._path(run_id)
        if not path.is_file():
            return None
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Checkpoint must contain a mapping: {path}")
        return payload


class FileEventStore:
    def __init__(self, project_root: Path):
        self.root = project_root.resolve() / ".project-os" / "runs" / "runtime" / "events"

    def _path(self, run_id: str) -> Path:
        return self.root / f"{_safe_id(run_id, 'run_id')}.jsonl"

    def append_event(self, event: dict[str, Any]) -> None:
        run_id = str(event.get("run_id", ""))
        path = self._path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def read_events(self, run_id: str) -> list[dict[str, Any]]:
        path = self._path(run_id)
        if not path.is_file():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"Event must be an object: {path}")
                events.append(payload)
        return events


class FileApprovalGateway:
    VALID_STATUSES = {"pending", "approved", "rejected"}

    def __init__(self, project_root: Path):
        self.root = project_root.resolve() / ".project-os" / "runs" / "runtime" / "approvals"

    def _path(self, approval_id: str) -> Path:
        return self.root / f"{_safe_id(approval_id, 'approval_id')}.yaml"

    def request(self, gate: str, payload: dict[str, Any]) -> str:
        gate_name = _safe_id(gate, "gate")
        canonical = json.dumps(
            {"gate": gate_name, "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]
        approval_id = f"approval-{digest}"
        path = self._path(approval_id)
        record = {
            "approval_id": approval_id,
            "gate": gate_name,
            "status": "pending",
            "payload": payload,
        }

        if path.is_file():
            existing = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if (
                existing.get("gate") != gate_name
                or existing.get("payload") != payload
            ):
                raise ValueError(f"Approval id collision: {approval_id}")
            return approval_id

        _atomic_yaml(path, record)
        return approval_id

    def status(self, approval_id: str) -> str:
        path = self._path(approval_id)
        if not path.is_file():
            raise KeyError(f"Unknown approval: {approval_id}")
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        status = str(payload.get("status", ""))
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid approval status in {path}: {status}")
        return status

    def resolve(self, approval_id: str, status: str) -> None:
        normalized = status.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError("Approval resolution must be approved or rejected")
        path = self._path(approval_id)
        if not path.is_file():
            raise KeyError(f"Unknown approval: {approval_id}")
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        current = str(payload.get("status", ""))
        if current in {"approved", "rejected"} and current != normalized:
            raise ValueError(
                f"Approval {approval_id} is already resolved as {current}"
            )
        payload["status"] = normalized
        _atomic_yaml(path, payload)
