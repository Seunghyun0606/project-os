from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


AgentHandler = Callable[
    [str, dict[str, Any], dict[str, Any]],
    Awaitable[dict[str, Any]],
]


class CallableAgentRunner:
    """Small native AgentRunner adapter around an async Python callable."""

    def __init__(self, handler: AgentHandler):
        self.handler = handler

    async def run(
        self,
        role: str,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        result = await self.handler(role, task, context)
        if not isinstance(result, dict):
            raise TypeError("AgentRunner must return a mapping")
        return result
