from __future__ import annotations

from typing import Any

from .control_service import CentralControlService


def _short_codex(value: str | None) -> str:
    if not value:
        return "-"
    return value if len(value) <= 18 else f"{value[:12]}..."


class SessionCommandHandler:
    """Transport-neutral slash command adapter for Telegram/other gateways."""

    def __init__(self, control: CentralControlService):
        self.control = control

    def handle(
        self,
        text: str,
        *,
        project_id: str,
        worker_id: str | None = None,
        created_by: str = "telegram",
    ) -> dict[str, Any] | None:
        command = " ".join(text.strip().split())
        if command == "/session":
            session = self.control.active_session(project_id)
            if session is None:
                return {
                    "handled": True,
                    "command": "session",
                    "message": f"Project: {project_id}\nSession: -\nStatus: none",
                    "payload": None,
                }
            return {
                "handled": True,
                "command": "session",
                "message": self._format_session(session),
                "payload": session,
            }

        if command == "/session new":
            session = self.control.new_session(
                project_id,
                created_by=created_by,
                worker_id=worker_id,
                title="Remote Session",
            )
            return {
                "handled": True,
                "command": "session_new",
                "message": (
                    f"New session: {session['session_id']}\n"
                    "Codex session will be created by the next job."
                ),
                "payload": session,
            }

        if command == "/sessions":
            sessions = self.control.list_sessions(project_id, limit=10)
            lines = [project_id, ""]
            if not sessions:
                lines.append("No sessions.")
            for session in sessions:
                marker = "*" if session["status"] in {"idle", "running"} else " "
                lines.append(
                    f"{marker} {session['session_id']}  {session['status']}  "
                    f"Codex {_short_codex(session.get('codex_session_id'))}"
                )
                lines.append(f"  Last activity {session['last_activity_at']}")
            return {
                "handled": True,
                "command": "sessions",
                "message": "\n".join(lines),
                "payload": sessions,
            }

        return None

    @staticmethod
    def _format_session(session: dict[str, Any]) -> str:
        return "\n".join(
            [
                f"Project: {session['project_id']}",
                f"Session: {session['session_id']}",
                f"Codex: {_short_codex(session.get('codex_session_id'))}",
                f"Status: {session['status']}",
                f"Last Job: {session.get('last_job_id') or '-'}",
                f"Last Activity: {session['last_activity_at']}",
            ]
        )
