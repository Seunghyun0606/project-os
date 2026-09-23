from pathlib import Path

import yaml

from projectctl.history import compact_run_history
from projectctl.project import Project
from projectctl.scaffold import install_scaffold


def _run(path: Path, run_id: str, finished_at: str, summary: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({
            "run_id": run_id,
            "task": "TASK-1",
            "role": "developer",
            "status": "completed",
            "finished_at": finished_at,
            "summary": summary,
            "events": [
                {"type": "tool"},
                {"type": "tool"},
                {"type": "result"},
            ],
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }, sort_keys=False),
        encoding="utf-8",
    )


def test_compaction_keeps_recent_runs_and_archives_older_runs(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    history = tmp_path / ".project-os/runs/history"
    _run(history / "001.yaml", "RUN-001", "2026-09-20T00:00:00Z", "first")
    _run(history / "002.yaml", "RUN-002", "2026-09-21T00:00:00Z", "second")
    _run(history / "003.yaml", "RUN-003", "2026-09-22T00:00:00Z", "third")

    result = compact_run_history(Project(tmp_path), keep_recent=1)

    assert result.compacted_runs == ["RUN-001", "RUN-002"]
    assert result.kept_runs == ["RUN-003"]
    assert (history / "003.yaml").exists()
    assert not (history / "001.yaml").exists()
    assert (tmp_path / ".project-os/runs/archive/001.yaml").exists()

    summary = yaml.safe_load(
        (tmp_path / ".project-os/runs/summaries/history.yaml").read_text(encoding="utf-8")
    )
    assert [item["run_id"] for item in summary["runs"]] == ["RUN-001", "RUN-002"]
    assert summary["runs"][0]["event_counts"] == {"result": 1, "tool": 2}
    assert "events" not in summary["runs"][0]


def test_compaction_is_idempotent(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    history = tmp_path / ".project-os/runs/history"
    _run(history / "001.yaml", "RUN-001", "2026-09-20T00:00:00Z", "first")
    _run(history / "002.yaml", "RUN-002", "2026-09-21T00:00:00Z", "second")

    project = Project(tmp_path)
    first = compact_run_history(project, keep_recent=1)
    second = compact_run_history(project, keep_recent=1)

    assert first.compacted_runs == ["RUN-001"]
    assert second.compacted_runs == []
    summary = yaml.safe_load(
        (tmp_path / ".project-os/runs/summaries/history.yaml").read_text(encoding="utf-8")
    )
    assert [item["run_id"] for item in summary["runs"]] == ["RUN-001"]


def test_compaction_preflights_archive_conflicts(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    history = tmp_path / ".project-os/runs/history"
    archive = tmp_path / ".project-os/runs/archive"
    _run(history / "001.yaml", "RUN-001", "2026-09-20T00:00:00Z", "first")
    _run(history / "002.yaml", "RUN-002", "2026-09-21T00:00:00Z", "second")
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "001.yaml").write_text("different: content\n", encoding="utf-8")

    try:
        compact_run_history(Project(tmp_path), keep_recent=1)
        raise AssertionError("expected FileExistsError")
    except FileExistsError:
        pass

    assert (history / "001.yaml").exists()
    assert not (tmp_path / ".project-os/runs/summaries/history.yaml").exists()


def test_compaction_rejects_duplicate_run_ids_before_writing(tmp_path: Path):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    history = tmp_path / ".project-os/runs/history"
    _run(history / "001.yaml", "RUN-001", "2026-09-20T00:00:00Z", "first")
    _run(history / "002.yaml", "RUN-001", "2026-09-21T00:00:00Z", "duplicate")

    try:
        compact_run_history(Project(tmp_path), keep_recent=0)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Duplicate run_id" in str(exc)

    assert not (tmp_path / ".project-os/runs/summaries/history.yaml").exists()
