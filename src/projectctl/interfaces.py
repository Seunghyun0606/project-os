from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class ProjectStore(Protocol):
    def load_yaml(self, relative_path: str) -> dict[str, Any]: ...
    def save_yaml(self, relative_path: str, data: dict[str, Any]) -> None: ...


class TaskScheduler(Protocol):
    def next_task(self, role: str) -> dict[str, Any] | None: ...


class ContextBuilder(Protocol):
    def build(self, task_id: str, role: str | None = None) -> dict[str, Any]: ...


class AgentRunner(Protocol):
    async def run(self, role: str, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...


class Orchestrator(Protocol):
    async def execute(self, workflow: str, project_root: Path) -> dict[str, Any]: ...


class CheckpointStore(Protocol):
    def save_checkpoint(self, run_id: str, state: dict[str, Any]) -> None: ...
    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None: ...


class EventStore(Protocol):
    def append_event(self, event: dict[str, Any]) -> None: ...


class ApprovalGateway(Protocol):
    def request(self, gate: str, payload: dict[str, Any]) -> str: ...
    def status(self, approval_id: str) -> str: ...
