from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Iterator, Tuple


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
    packaged = files("projectctl").joinpath("_scaffold", "default")
    if packaged.is_dir():
        return packaged

    development = Path(__file__).resolve().parents[2] / "scaffold" / "default"
    if development.is_dir():
        return development

    raise RuntimeError("Project OS scaffold resources were not packaged correctly.")


def iter_files(root) -> Iterator[Tuple[object, Path]]:
    def walk(current, prefix: Path):
        for entry in current.iterdir():
            relative = prefix / entry.name
            if entry.is_dir():
                yield from walk(entry, relative)
            elif entry.is_file():
                yield entry, relative

    yield from walk(root, Path())


def install_scaffold(
    target: Path,
    project_id: str,
    project_name: str,
    force: bool = False,
) -> None:
    target = target.resolve()
    template = scaffold_root()
    entries = list(iter_files(template))

    if not force:
        conflicts = [
            target / relative
            for _, relative in entries
            if (target / relative).exists()
        ]
        if conflicts:
            preview = ", ".join(str(path) for path in conflicts[:5])
            if len(conflicts) > 5:
                preview += f", ... (+{len(conflicts) - 5} more)"
            raise FileExistsError(
                f"Refusing to modify an existing project because scaffold files already exist: {preview}"
            )

    for entry, relative in entries:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = entry.read_text(encoding="utf-8")
        content = content.replace("__PROJECT_ID__", project_id)
        content = content.replace("__PROJECT_NAME__", project_name)
        destination.write_text(content, encoding="utf-8")

    for relative in EMPTY_DIRECTORIES:
        (target / relative).mkdir(parents=True, exist_ok=True)
