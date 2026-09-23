from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from . import __version__
from .context import FileContextBuilder
from .doctor import inspect
from .handoffs import EvaluationService, HandoffStore, resolve_actor
from .history import compact_run_history
from .project import Project
from .roles import RolePolicyResolver
from .transitions import CanonicalStateWriter
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
    try:
        CanonicalStateWriter(project).claim(task_id, role)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Claimed {task_id}")


def _load_handoff_file(path: Path) -> dict:
    if not path.exists():
        raise typer.BadParameter(f"Result file does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise typer.BadParameter(f"Result file must contain a mapping: {path}")
    return payload


def _task_role(project: Project, task_id: str) -> str:
    for task in project.backlog().get("tasks", []) or []:
        if task.get("id") == task_id:
            return str(task.get("role", "developer"))
    raise typer.BadParameter(f"Unknown task: {task_id}")


@app.command()
def submit(
    task_id: str,
    result_file: Path,
    role: Optional[str] = typer.Option(None, "--role"),
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store implementation output without self-approving completion."""
    project = Project.open()
    payload = _load_handoff_file(result_file)
    resolved_role = role or _task_role(project, task_id)
    resolved_actor = resolve_actor(actor, resolved_role)
    try:
        destination = HandoffStore(project).submit(
            task_id=task_id,
            kind="implementation",
            payload=payload,
            role=resolved_role,
            actor=resolved_actor,
        )
    except (ValueError, PermissionError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(
        f"Stored implementation result at {destination.relative_to(project.root)}. "
        "Completion still requires independent quality evaluation."
    )


@app.command("review")
def submit_review(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store an independent reviewer handoff."""
    project = Project.open()
    payload = _load_handoff_file(result_file)
    try:
        destination = HandoffStore(project).submit(
            task_id=task_id,
            kind="review",
            payload=payload,
            role="reviewer",
            actor=resolve_actor(actor, "reviewer"),
        )
    except (ValueError, PermissionError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Stored review result at {destination.relative_to(project.root)}")


@app.command("qa")
def submit_qa(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store an independent QA handoff."""
    project = Project.open()
    payload = _load_handoff_file(result_file)
    try:
        destination = HandoffStore(project).submit(
            task_id=task_id,
            kind="qa",
            payload=payload,
            role="qa",
            actor=resolve_actor(actor, "qa"),
        )
    except (ValueError, PermissionError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Stored QA result at {destination.relative_to(project.root)}")


@app.command("evaluate")
def evaluate_task(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Evaluate evidence and apply the only completion-state transition path."""
    project = Project.open()
    payload = _load_handoff_file(result_file)
    try:
        destination = EvaluationService(project).evaluate(
            task_id=task_id,
            payload=payload,
            actor=resolve_actor(actor, "evaluator"),
        )
    except (ValueError, PermissionError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    decision = str(payload.get("decision", payload.get("status", ""))).upper()
    typer.echo(
        f"Stored evaluation at {destination.relative_to(project.root)}; "
        f"canonical task decision: {decision}"
    )


@app.command("role-policy")
def role_policy(
    role: str,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show the resolved role policy after project overrides."""
    try:
        payload = RolePolicyResolver(Project.open()).resolve(role)
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip())


@app.command("compact-runs")
def compact_runs(
    keep_recent: int = typer.Option(20, "--keep-recent", help="Number of newest raw runs to keep."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Compact old structured run history without deleting raw evidence."""
    try:
        result = compact_run_history(Project.open(), keep_recent=keep_recent)
    except (ValueError, FileExistsError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    payload = result.as_dict()
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(
        f"Compacted {len(result.compacted_runs)} run(s); "
        f"kept {len(result.kept_runs)} recent run(s)."
    )
    if result.summary_path:
        typer.echo(f"Summary: {result.summary_path}")


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
