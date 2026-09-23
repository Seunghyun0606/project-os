from __future__ import annotations

from importlib.resources import files
from pathlib import Path


EMPTY_DIRECTORIES = [
    ".project-os/milestones",
    ".project-os/tasks/ready",
    ".project-os/tasks/active",
    ".project-os/tasks/blocked",
    ".project-os/tasks/completed",
    ".project-os/tasks/results",
    ".project-os/decisions",
    ".project-os/runs/summaries",
    "specs/product",
    "specs/feature",
    "specs/architecture",
    "specs/ux",
]


def scaffold_root():
    return files("projectctl").joinpath("_scaffold", "default")


def install_scaffold(
    target: Path,
    project_id: str,
    project_name: str,
    force: bool = False,
) -> None:
    target = target.resolve()
    template = scaffold_root()

    for entry in template.rglob("*"):
        if not entry.is_file():
            continue
        relative = entry.relative_to(template)
        destination = target / str(relative)
        if destination.exists() and not force:
            raise FileExistsError(
                f"Refusing to overwrite {destination}. Use --force if intentional."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = entry.read_text(encoding="utf-8")
        content = content.replace("__PROJECT_ID__", project_id)
        content = content.replace("__PROJECT_NAME__", project_name)
        destination.write_text(content, encoding="utf-8")

    for relative in EMPTY_DIRECTORIES:
        (target / relative).mkdir(parents=True, exist_ok=True)
