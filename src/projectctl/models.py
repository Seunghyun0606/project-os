from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskRecord(BaseModel):
    id: str
    title: str = ""
    role: str = "developer"
    milestone: str | None = None
    priority: str = "P2"
    status: str = "planned"
    depends_on: list[str] = Field(default_factory=list)
    human_gate: bool = False
    contract: str | None = None


class ProjectStatus(BaseModel):
    project_id: str
    project_name: str
    project_status: str
    current_milestone: str | None
    current_tasks: list[str]
    blocked_tasks: list[str]
    human_gate: bool


class ContextPackage(BaseModel):
    task: dict[str, Any]
    project_file: str
    specs: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    active_decisions: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)
    verification: list[str] = Field(default_factory=list)
