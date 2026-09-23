from __future__ import annotations

from typing import Any

from .central_store import CentralControlStore


class SqliteCheckpointStore:
    def __init__(self, store: CentralControlStore):
        self.store = store

    def save_checkpoint(self, run_id: str, state: dict[str, Any]) -> None:
        self.store.save_checkpoint(run_id, state)

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        return self.store.load_checkpoint(run_id)


class SqliteEventStore:
    def __init__(
        self,
        store: CentralControlStore,
        project_id: str | None = None,
    ):
        self.store = store
        self.project_id = project_id

    def append_event(self, event: dict[str, Any]) -> None:
        payload = dict(event)
        if self.project_id and not payload.get("project_id"):
            payload["project_id"] = self.project_id
        self.store.append_event(payload)

    def read_events(self, run_id: str) -> list[dict[str, Any]]:
        return self.store.read_events(run_id)


class SqliteApprovalGateway:
    def __init__(self, store: CentralControlStore):
        self.store = store

    def request(self, gate: str, payload: dict[str, Any]) -> str:
        return self.store.request_approval(gate, payload)

    def status(self, approval_id: str) -> str:
        return self.store.approval_status(approval_id)

    def resolve(self, approval_id: str, status: str) -> None:
        self.store.resolve_approval(approval_id, status)
