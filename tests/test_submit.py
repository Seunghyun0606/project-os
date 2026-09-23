from pathlib import Path

import yaml
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.scaffold import install_scaffold


runner = CliRunner()


def test_submit_stores_result_without_completing_task(tmp_path: Path, monkeypatch):
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    backlog_path = tmp_path / ".project-os/state/backlog.yaml"
    backlog_path.write_text(
        yaml.safe_dump({
            "tasks": [{
                "id": "TASK-1",
                "title": "Implement",
                "role": "developer",
                "status": "active",
            }]
        }),
        encoding="utf-8",
    )
    result_path = tmp_path / "result.yaml"
    result_path.write_text(
        yaml.safe_dump({
            "task": "TASK-1",
            "status": "done",
            "summary": "Implementation finished",
        }),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["submit", "TASK-1", str(result_path)])

    assert result.exit_code == 0
    stored = yaml.safe_load(
        (tmp_path / ".project-os/tasks/results/TASK-1.yaml").read_text(encoding="utf-8")
    )
    backlog = yaml.safe_load(backlog_path.read_text(encoding="utf-8"))
    assert stored["task"] == "TASK-1"
    assert backlog["tasks"][0]["status"] == "active"
