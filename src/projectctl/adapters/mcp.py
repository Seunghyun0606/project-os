from __future__ import annotations

from typing import Any

from ..harness_models import HarnessResult
from ..service import ProjectService


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


class McpToolAdapter:
    """Transport-neutral MCP tool surface backed only by ProjectService."""

    def __init__(self, service: ProjectService):
        self.service = service

    def list_tools(self) -> list[dict[str, Any]]:
        payload = {"type": "object", "additionalProperties": True}
        actor = {"type": "string", "minLength": 1}
        task_id = {"type": "string", "minLength": 1}
        role = {"type": "string", "minLength": 1}

        return [
            {
                "name": "get_status",
                "description": "Get the canonical Project OS status snapshot.",
                "inputSchema": _object({}),
            },
            {
                "name": "get_next_task",
                "description": "Get the next deterministic eligible task for a role.",
                "inputSchema": _object({"role": role}),
            },
            {
                "name": "build_context",
                "description": "Build bounded role/task context without scanning the whole repository.",
                "inputSchema": _object(
                    {"task_id": task_id, "role": role},
                    ["task_id"],
                ),
            },
            {
                "name": "claim_task",
                "description": "Claim the next eligible task through the canonical state writer.",
                "inputSchema": _object(
                    {"task_id": task_id, "role": role},
                    ["task_id"],
                ),
            },
            {
                "name": "submit_result",
                "description": "Store an implementation handoff without completing the task.",
                "inputSchema": _object(
                    {
                        "task_id": task_id,
                        "payload": payload,
                        "role": role,
                        "actor": actor,
                    },
                    ["task_id", "payload"],
                ),
            },
            {
                "name": "submit_review",
                "description": "Store an independent review handoff.",
                "inputSchema": _object(
                    {"task_id": task_id, "payload": payload, "actor": actor},
                    ["task_id", "payload"],
                ),
            },
            {
                "name": "submit_qa",
                "description": "Store an independent QA handoff.",
                "inputSchema": _object(
                    {"task_id": task_id, "payload": payload, "actor": actor},
                    ["task_id", "payload"],
                ),
            },
            {
                "name": "record_test_result",
                "description": "Record structured automated verification evidence.",
                "inputSchema": _object(
                    {"task_id": task_id, "payload": payload, "actor": actor},
                    ["task_id", "payload"],
                ),
            },
            {
                "name": "evaluate_task",
                "description": "Evaluate configured evidence and apply the validated task transition.",
                "inputSchema": _object(
                    {"task_id": task_id, "payload": payload, "actor": actor},
                    ["task_id", "payload"],
                ),
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        args = dict(arguments or {})
        routes = {
            "get_status": lambda: self.service.get_status(),
            "get_next_task": lambda: self.service.get_next_task(
                role=str(args.get("role", "developer"))
            ),
            "build_context": lambda: self.service.build_context(
                task_id=str(args["task_id"]),
                role=str(args["role"]) if args.get("role") else None,
            ),
            "claim_task": lambda: self.service.claim_task(
                task_id=str(args["task_id"]),
                role=str(args.get("role", "developer")),
            ),
            "submit_result": lambda: self.service.submit_result(
                task_id=str(args["task_id"]),
                payload=dict(args["payload"]),
                role=str(args["role"]) if args.get("role") else None,
                actor=str(args["actor"]) if args.get("actor") else None,
            ),
            "submit_review": lambda: self.service.submit_review(
                task_id=str(args["task_id"]),
                payload=dict(args["payload"]),
                actor=str(args["actor"]) if args.get("actor") else None,
            ),
            "submit_qa": lambda: self.service.submit_qa(
                task_id=str(args["task_id"]),
                payload=dict(args["payload"]),
                actor=str(args["actor"]) if args.get("actor") else None,
            ),
            "record_test_result": lambda: self.service.record_test_result(
                task_id=str(args["task_id"]),
                payload=dict(args["payload"]),
                actor=str(args["actor"]) if args.get("actor") else None,
            ),
            "evaluate_task": lambda: self.service.evaluate_task(
                task_id=str(args["task_id"]),
                payload=dict(args["payload"]),
                actor=str(args["actor"]) if args.get("actor") else None,
            ),
        }

        route = routes.get(name)
        if route is None:
            return HarnessResult.failure(
                "mcp.call_tool",
                "unknown_tool",
                f"Unknown Project OS tool: {name}",
            ).model_dump()

        try:
            return route().model_dump()
        except (KeyError, TypeError, ValueError) as exc:
            return HarnessResult.failure(
                name,
                "invalid_request",
                str(exc),
            ).model_dump()
