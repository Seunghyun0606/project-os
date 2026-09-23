from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .project import Project


_RUN_SUFFIXES = {".yaml", ".yml", ".json"}


@dataclass(frozen=True)
class CompactionResult:
    compacted_runs: list[str]
    kept_runs: list[str]
    archived_paths: list[str]
    summary_path: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "compacted_runs": self.compacted_runs,
            "kept_runs": self.kept_runs,
            "archived_paths": self.archived_paths,
            "summary_path": self.summary_path,
        }


def _load_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Cannot read run history file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Run history file must contain a mapping: {path}")
    return payload


def _timestamp(payload: dict[str, Any]) -> float:
    raw = (
        payload.get("finished_at")
        or payload.get("started_at")
        or payload.get("created_at")
        or ""
    )
    if not raw:
        return float("-inf")
    try:
        value = str(raw).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return float("-inf")


def _event_counts(payload: dict[str, Any]) -> dict[str, int]:
    events = payload.get("events", []) or []
    if not isinstance(events, list):
        return {}
    counts = Counter(
        str(event.get("type", "unknown"))
        for event in events
        if isinstance(event, dict)
    )
    return dict(sorted(counts.items()))


def _summary_entry(payload: dict[str, Any], archived_path: str) -> dict[str, Any]:
    run_id = str(payload.get("run_id", ""))
    if not run_id:
        raise ValueError("Run history record is missing run_id")

    entry: dict[str, Any] = {
        "run_id": run_id,
        "task": payload.get("task"),
        "role": payload.get("role"),
        "status": payload.get("status"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "summary": payload.get("summary"),
        "artifacts": list(payload.get("artifacts", []) or []),
        "evidence": list(payload.get("evidence", []) or []),
        "usage": payload.get("usage"),
        "event_counts": _event_counts(payload),
        "source": archived_path,
    }
    return {key: value for key, value in entry.items() if value not in (None, [], {}, "")}


def _history_files(history_root: Path) -> list[Path]:
    if not history_root.is_dir():
        return []
    return sorted(
        path
        for path in history_root.rglob("*")
        if path.is_file() and path.suffix.lower() in _RUN_SUFFIXES
    )


def compact_run_history(
    project: Project,
    keep_recent: int = 20,
) -> CompactionResult:
    if keep_recent < 0:
        raise ValueError("keep_recent must be zero or greater")

    os_root = project.root / ".project-os"
    history_root = os_root / "runs" / "history"
    archive_root = os_root / "runs" / "archive"
    summaries_root = os_root / "runs" / "summaries"
    summary_file = summaries_root / "history.yaml"

    records: list[tuple[Path, dict[str, Any]]] = []
    seen_ids: set[str] = set()
    for path in _history_files(history_root):
        payload = _load_mapping(path)
        run_id = str(payload.get("run_id", ""))
        if not run_id:
            raise ValueError(f"Run history record is missing run_id: {path}")
        if run_id in seen_ids:
            raise ValueError(f"Duplicate run_id in history: {run_id}")
        seen_ids.add(run_id)
        records.append((path, payload))

    records.sort(
        key=lambda item: (
            _timestamp(item[1]),
            str(item[1].get("run_id", "")),
            item[0].relative_to(history_root).as_posix(),
        )
    )

    split = max(0, len(records) - keep_recent)
    compacted = records[:split]
    kept = records[split:]

    if not compacted:
        return CompactionResult(
            compacted_runs=[],
            kept_runs=[str(payload["run_id"]) for _, payload in kept],
            archived_paths=[],
            summary_path=(
                summary_file.relative_to(project.root).as_posix()
                if summary_file.is_file()
                else None
            ),
        )

    existing: dict[str, Any] = {"version": 1, "runs": []}
    if summary_file.is_file():
        existing = _load_mapping(summary_file)
        if not isinstance(existing.get("runs", []), list):
            raise ValueError(f"Run summary file has invalid runs list: {summary_file}")

    existing_by_id: dict[str, dict[str, Any]] = {}
    for entry in existing.get("runs", []) or []:
        if not isinstance(entry, dict) or not entry.get("run_id"):
            raise ValueError(f"Run summary file contains an invalid entry: {summary_file}")
        run_id = str(entry["run_id"])
        if run_id in existing_by_id:
            raise ValueError(f"Duplicate run_id in summary: {run_id}")
        existing_by_id[run_id] = entry

    moves: list[tuple[Path, Path, str]] = []
    new_entries: dict[str, dict[str, Any]] = dict(existing_by_id)
    for source, payload in compacted:
        relative = source.relative_to(history_root)
        destination = archive_root / relative
        archived_relative = destination.relative_to(project.root).as_posix()
        entry = _summary_entry(payload, archived_relative)
        run_id = entry["run_id"]

        previous = existing_by_id.get(run_id)
        if previous is not None and previous != entry:
            raise ValueError(f"Run summary conflict for run_id {run_id}")

        if destination.exists():
            if destination.read_bytes() != source.read_bytes():
                raise FileExistsError(
                    f"Archive destination already exists with different content: {destination}"
                )
        new_entries[run_id] = entry
        moves.append((source, destination, run_id))

    summary_payload = {
        "version": 1,
        "runs": [new_entries[key] for key in sorted(new_entries)],
    }

    summaries_root.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(
        yaml.safe_dump(summary_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    archived_paths: list[str] = []
    for source, destination, _ in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            source.unlink()
        else:
            source.replace(destination)
        archived_paths.append(destination.relative_to(project.root).as_posix())

    return CompactionResult(
        compacted_runs=[str(payload["run_id"]) for _, payload in compacted],
        kept_runs=[str(payload["run_id"]) for _, payload in kept],
        archived_paths=archived_paths,
        summary_path=summary_file.relative_to(project.root).as_posix(),
    )
