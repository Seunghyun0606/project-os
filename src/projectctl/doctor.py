from __future__ import annotations

from dataclasses import dataclass

from .project import Project


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

    try:
        tasks = list(project.backlog().get("tasks", []) or [])
    except Exception as exc:
        findings.append(Finding("ERROR", f"Cannot read backlog: {exc}"))
        return findings

    ids = [str(task.get("id")) for task in tasks if task.get("id")]
    for task_id in sorted({x for x in ids if ids.count(x) > 1}):
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

    for node in graph:
        if visit(node):
            findings.append(Finding("ERROR", "Task dependency cycle detected"))
            break

    if not findings:
        findings.append(Finding("PASS", "Project OS structure and backlog references are consistent"))

    return findings
