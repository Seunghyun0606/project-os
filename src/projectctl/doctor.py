from __future__ import annotations

from dataclasses import dataclass

from . import __version__
from .project import Project
from .versioning import check_compatibility


@dataclass
class Finding:
    level: str
    message: str


REQUIRED = [
    "PROJECT.md",
    "AGENTS.md",
    ".project-os/manifest.yaml",
    ".project-os/profile.yaml",
    ".project-os/state/current.yaml",
    ".project-os/state/roadmap.yaml",
    ".project-os/state/backlog.yaml",
    ".project-os/quality/gates.yaml",
    ".project-os/context/index.yaml",
]


def inspect(project: Project) -> list[Finding]:
    findings: list[Finding] = []

    for rel in REQUIRED:
        if not (project.root / rel).exists():
            findings.append(Finding("ERROR", f"Missing required file: {rel}"))

    project_os = project.manifest.get("project_os", {}) or {}
    compatibility = check_compatibility(
        __version__,
        project_os.get("package_compatibility"),
    )
    if not compatibility.compatible:
        findings.append(Finding("ERROR", compatibility.reason))

    schema_version = str(project_os.get("schema_version", ""))
    if not schema_version:
        findings.append(Finding("ERROR", "Manifest is missing project_os.schema_version"))

    try:
        tasks = list(project.backlog().get("tasks", []) or [])
    except Exception as exc:
        findings.append(Finding("ERROR", f"Cannot read backlog: {exc}"))
        return findings

    missing_id_count = sum(1 for task in tasks if not task.get("id"))
    if missing_id_count:
        findings.append(Finding("ERROR", f"{missing_id_count} backlog task(s) are missing an id"))

    ids = [str(task.get("id")) for task in tasks if task.get("id")]
    counts = {task_id: ids.count(task_id) for task_id in set(ids)}
    for task_id in sorted(task_id for task_id, count in counts.items() if count > 1):
        findings.append(Finding("ERROR", f"Duplicate task id: {task_id}"))

    known = set(ids)
    for task in tasks:
        task_id = str(task.get("id", "<unknown>"))
        for dep in task.get("depends_on", []) or []:
            if dep not in known:
                findings.append(Finding("ERROR", f"{task_id} depends on missing task {dep}"))

    graph = {
        str(task.get("id")): list(task.get("depends_on", []) or [])
        for task in tasks
        if task.get("id")
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in graph and visit(dep):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    for node in sorted(graph):
        if visit(node):
            findings.append(Finding("ERROR", "Task dependency cycle detected"))
            break

    if not findings:
        findings.append(Finding("PASS", "Project OS structure and backlog references are consistent"))

    return findings
