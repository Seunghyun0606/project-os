import json
from pathlib import Path

from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.scaffold import install_scaffold


runner = CliRunner()


def test_control_cli_register_list_and_dashboard(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    install_scaffold(root, project_id="demo", project_name="Demo")
    db = tmp_path / "central" / "control.db"

    registered = runner.invoke(
        app,
        [
            "control",
            "register",
            str(root),
            "--db",
            str(db),
            "--json",
        ],
    )
    listed = runner.invoke(
        app,
        ["control", "list", "--db", str(db), "--json"],
    )
    dashboard = runner.invoke(
        app,
        ["control", "dashboard", "--db", str(db), "--json"],
    )

    assert registered.exit_code == 0, registered.output
    assert listed.exit_code == 0, listed.output
    assert dashboard.exit_code == 0, dashboard.output

    registered_payload = json.loads(registered.output)
    listed_payload = json.loads(listed.output)
    dashboard_payload = json.loads(dashboard.output)

    assert registered_payload["project_id"] == "demo"
    assert listed_payload["projects"][0]["project_id"] == "demo"
    assert dashboard_payload["project_count"] == 1
    assert db.exists()
    assert not (root / ".project-os/control.db").exists()


def test_control_cli_usage_and_budget(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    install_scaffold(root, project_id="demo", project_name="Demo")
    db = tmp_path / "control.db"

    assert runner.invoke(
        app,
        ["control", "register", str(root), "--db", str(db)],
    ).exit_code == 0

    policy = runner.invoke(
        app,
        [
            "control",
            "policy-set",
            "demo",
            "developer",
            "openai",
            "gpt-test",
            "--max-cost",
            "1.0",
            "--db",
            str(db),
        ],
    )
    usage = runner.invoke(
        app,
        [
            "control",
            "usage-record",
            "demo",
            "openai",
            "gpt-test",
            "--role",
            "developer",
            "--input-tokens",
            "100",
            "--output-tokens",
            "20",
            "--cost",
            "0.25",
            "--db",
            str(db),
        ],
    )
    budget = runner.invoke(
        app,
        [
            "control",
            "budget",
            "demo",
            "developer",
            "--db",
            str(db),
            "--json",
        ],
    )

    assert policy.exit_code == 0, policy.output
    assert usage.exit_code == 0, usage.output
    assert budget.exit_code == 0, budget.output
    payload = json.loads(budget.output)
    assert payload["spent"] == 0.25
    assert payload["remaining"] == 0.75
    assert payload["exceeded"] is False


def test_control_cli_migration_assess_does_not_change_manifest(tmp_path: Path):
    root = tmp_path / "project"
    root.mkdir()
    install_scaffold(root, project_id="demo", project_name="Demo")
    db = tmp_path / "control.db"
    manifest = root / ".project-os/manifest.yaml"
    before = manifest.read_text(encoding="utf-8")

    runner.invoke(app, ["control", "register", str(root), "--db", str(db)])
    result = runner.invoke(
        app,
        [
            "control",
            "migration-assess",
            "demo",
            "2",
            "--db",
            str(db),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["status"] == "migration_required"
    assert manifest.read_text(encoding="utf-8") == before
