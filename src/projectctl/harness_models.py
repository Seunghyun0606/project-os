from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HarnessError(BaseModel):
    code: str
    message: str


class HarnessResult(BaseModel):
    version: int = 1
    ok: bool
    action: str
    data: dict[str, Any] | None = None
    error: HarnessError | None = None

    @classmethod
    def success(cls, action: str, data: dict[str, Any] | None = None) -> "HarnessResult":
        return cls(ok=True, action=action, data=data or {})

    @classmethod
    def failure(cls, action: str, code: str, message: str) -> "HarnessResult":
        return cls(
            ok=False,
            action=action,
            data=None,
            error=HarnessError(code=code, message=message),
        )
