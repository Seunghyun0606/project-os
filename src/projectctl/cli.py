from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer
import yaml

from . import __version__
from .context import FileContextBuilder
from .doctor import inspect
from .project import Project
from .scaffold import install_scaffold
from .scheduler import DeterministicTaskScheduler

app = typer.Typer(
    no_args_is_help=True,
    help="Project OS deterministic project control CLI.",
)


@app.command()
def version() -> None:
    """Show the installed projectctl version."""
    typer.echo(__version__)


@app.command("init")
def init_project(
    project_id: Optional[str] = typer.Option(None, "--project-id", help="Stable project id."),
    name: Optional[str] = typer.Option(None, "--name", help="Human-readable project name."),
    path: Path = typer.Option(Path("."), "--path", help="Target project root."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing scaffold files."),
) -> None:
    """Install only the consumer scaffold into a project."""
    target = path.resolve()
    resolved_id = project_id or target.name.lower().replace(" ", "-")
    resolved_name = name or target.name
    install_scaffold(
        target,
        project_id=resolved_id,
        project_name=resolved_name,
        force=force,
    )
    typer.echo(f"Project OS scaffold installed at {target}")


@app.command()
def status(json_output: bool = typer.Option(False, "--json")) -> None:
    """Show the current canonical project snapshot."""
    payload = Project.open().status().model_dump()
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


@app.command("next")
def next_task(
    role: str = typer.Option("developer", "--role"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Select the highest-priority ready task whose dependencies are done."""
    project = Project.open()
    task = DeterministicTaskScheduler(project).next_task(role)
    if task is None:
        typer.echo("No eligible task.")
        raise typer.Exit(code=2)
    if json_output:
        typer.echo(json.dumps(task, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"{task.get('id')}: {task.get('title', '')}")


@app.command()
def context(
    task_id: str,
    role: Optional[str] = typer.Option(None, "--role"),
) -> None:
    """Build a small structured context package for a task."""
    payload = FileContextBuilder(Project.open()).build(task_id, role)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def claim(
    task_id: str,
    role: str = typer.Option("developer", "--role"),
) -> None:
    """Move the next eligible task to active state."""
    project = Project.open()
    selected = DeterministicTaskScheduler(project).next_task(role)
    if selected is None or selected.get("id") != task_id:
        raise typer.BadParameter(
            f"{task_id} is not the next eligible task for role {role}"
        )

    backlog = project.backlog()
    for task in backlog.get("tasks", []):
        if task.get("id") == task_id:
            task["status"] = "active"
            break
    project.store.save_yaml("state/backlog.yaml", backlog)

    state = project.current_state()
    current = list(state.get("current_tasks", []) or [])
    if task_id not in current:
        current.append(task_id)
    state["current_tasks"] = current
    project.store.save_yaml("state/current.yaml", state)
    typer.echo(f"Claimed {task_id}")


@app.command()
def submit(task_id: str, result_file: Path) -> None:
    """Store a task result without self-approving completion."""
    project = Project.open()
    if not result_file.exists():
        raise typer.BadParameter(f"Result file does not exist: {result_file}")

    payload = yaml.safe_load(result_file.read_text(encoding="utf-8")) or {}
    if payload.get("task") != task_id:
        raise typer.BadParameter(
            "Result file task id does not match the command task id"
        )

    destination = (
        project.root / ".project-os" / "tasks" / "results" / f"{task_id}.yaml"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result_file, destination)
    typer.echo(
        f"Stored result for {task_id}. Completion still requires quality evaluation."
    )


@app.command()
def doctor() -> None:
    """Check required files, task references and dependency consistency."""
    findings = inspect(Project.open())
    has_error = False
    for finding in findings:
        typer.echo(f"{finding.level}: {finding.message}")
        has_error = has_error or finding.level == "ERROR"
    if has_error:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
