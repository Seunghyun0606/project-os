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
    ".project-os/runs/runtime/checkpoints",
    ".project-os/runs/runtime/events",
    ".project-os/runs/runtime/approvals",
    ".project-os/workflows",
    "specs/product",
    "specs/feature",
    "specs/architecture",
    "specs/ux",
]

QA_EMPTY_DIRECTORIES = [
    ".qa/runs",
]


def _scaffold_root(name: str):
    packaged = files("projectctl").joinpath("_scaffold", name)
    if packaged.is_dir():
        return packaged

    development = Path(__file__).resolve().parents[2] / "scaffold" / name
    if development.is_dir():
        return development

    raise RuntimeError(
        f"Project OS scaffold resources were not packaged correctly: {name}"
    )


def scaffold_root():
    return _scaffold_root("default")


def qa_scaffold_root():
    return _scaffold_root("qa")


def iter_files(root) -> Iterator[Tuple[object, Path]]:
    def walk(current, prefix: Path):
        for entry in current.iterdir():
            relative = prefix / entry.name
            if entry.is_dir():
                yield from walk(entry, relative)
            elif entry.is_file():
                yield entry, relative

    yield from walk(root, Path())


def _install_entries(
    target: Path,
    entries: list[tuple[object, Path]],
    *,
    project_id: str,
    project_name: str,
    force: bool,
) -> None:
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
                "Refusing to modify an existing project because scaffold files "
                f"already exist: {preview}"
            )

    for entry, relative in entries:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = entry.read_text(encoding="utf-8")
        content = content.replace("__PROJECT_ID__", project_id)
        content = content.replace("__PROJECT_NAME__", project_name)
        destination.write_text(content, encoding="utf-8")


def install_scaffold(
    target: Path,
    project_id: str,
    project_name: str,
    force: bool = False,
    with_qa: bool = False,
) -> None:
    target = target.resolve()
    entries = list(iter_files(scaffold_root()))
    directories = list(EMPTY_DIRECTORIES)

    if with_qa:
        entries.extend(iter_files(qa_scaffold_root()))
        directories.extend(QA_EMPTY_DIRECTORIES)

    _install_entries(
        target,
        entries,
        project_id=project_id,
        project_name=project_name,
        force=force,
    )

    for relative in directories:
        (target / relative).mkdir(parents=True, exist_ok=True)


def install_qa_scaffold(
    target: Path,
    project_id: str,
    project_name: str,
    force: bool = False,
) -> None:
    target = target.resolve()
    entries = list(iter_files(qa_scaffold_root()))

    _install_entries(
        target,
        entries,
        project_id=project_id,
        project_name=project_name,
        force=force,
    )

    for relative in QA_EMPTY_DIRECTORIES:
        (target / relative).mkdir(parents=True, exist_ok=True)
