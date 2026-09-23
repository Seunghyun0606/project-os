from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from . import __version__
from .doctor import inspect
from .history import compact_run_history
from .project import Project
from .roles import RolePolicyResolver
from .runtime_stores import FileApprovalGateway, FileCheckpointStore
from .scaffold import install_scaffold
from .service import ProjectService

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


def _service_data(result) -> dict:
    if not result.ok:
        message = result.error.message if result.error else "Project OS request failed"
        raise typer.BadParameter(message)
    return result.data or {}


@app.command()
def status(json_output: bool = typer.Option(False, "--json")) -> None:
    """Show the current canonical project snapshot."""
    payload = _service_data(ProjectService.open().get_status())
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
    payload = _service_data(ProjectService.open().get_next_task(role))
    task = payload.get("task")
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
    payload = _service_data(ProjectService.open().build_context(task_id, role))
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def claim(
    task_id: str,
    role: str = typer.Option("developer", "--role"),
) -> None:
    """Move the next eligible task to active state."""
    payload = _service_data(ProjectService.open().claim_task(task_id, role))
    typer.echo(f"Claimed {payload['task_id']}")


def _load_handoff_file(path: Path) -> dict:
    if not path.exists():
        raise typer.BadParameter(f"Result file does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise typer.BadParameter(f"Result file must contain a mapping: {path}")
    return payload


@app.command()
def submit(
    task_id: str,
    result_file: Path,
    role: Optional[str] = typer.Option(None, "--role"),
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store implementation output without self-approving completion."""
    payload = _load_handoff_file(result_file)
    data = _service_data(
        ProjectService.open().submit_result(
            task_id=task_id,
            payload=payload,
            role=role,
            actor=actor,
        )
    )
    typer.echo(
        f"Stored implementation result at {data['path']}. "
        "Completion still requires independent quality evaluation."
    )


@app.command("review")
def submit_review(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store an independent reviewer handoff."""
    payload = _load_handoff_file(result_file)
    data = _service_data(
        ProjectService.open().submit_review(
            task_id=task_id,
            payload=payload,
            actor=actor,
        )
    )
    typer.echo(f"Stored review result at {data['path']}")


@app.command("qa")
def submit_qa(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store an independent QA handoff."""
    payload = _load_handoff_file(result_file)
    data = _service_data(
        ProjectService.open().submit_qa(
            task_id=task_id,
            payload=payload,
            actor=actor,
        )
    )
    typer.echo(f"Stored QA result at {data['path']}")


@app.command("record-test")
def record_test_result(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Store automated verification evidence separately from implementation output."""
    payload = _load_handoff_file(result_file)
    data = _service_data(
        ProjectService.open().record_test_result(
            task_id=task_id,
            payload=payload,
            actor=actor,
        )
    )
    typer.echo(f"Stored test result at {data['path']}")


@app.command("evaluate")
def evaluate_task(
    task_id: str,
    result_file: Path,
    actor: Optional[str] = typer.Option(None, "--actor"),
) -> None:
    """Evaluate evidence and apply the only completion-state transition path."""
    payload = _load_handoff_file(result_file)
    data = _service_data(
        ProjectService.open().evaluate_task(
            task_id=task_id,
            payload=payload,
            actor=actor,
        )
    )
    typer.echo(
        f"Stored evaluation at {data['path']}; "
        f"canonical task decision: {data['decision']}"
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


@app.command("runtime-status")
def runtime_status(
    run_id: str,
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show workflow runtime checkpoint state without reading canonical project state."""
    payload = FileCheckpointStore(Project.open().root).load_checkpoint(run_id)
    if payload is None:
        raise typer.BadParameter(f"Unknown runtime run: {run_id}")
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True).rstrip())


@app.command("approval-status")
def approval_status(approval_id: str) -> None:
    """Show the current status of a native workflow approval."""
    try:
        status = FileApprovalGateway(Project.open().root).status(approval_id)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(status)


@app.command("approval-resolve")
def approval_resolve(
    approval_id: str,
    status: str = typer.Argument(..., help="approved or rejected"),
) -> None:
    """Resolve a pending native workflow approval."""
    try:
        FileApprovalGateway(Project.open().root).resolve(approval_id, status)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"{approval_id}: {status.lower()}")


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
