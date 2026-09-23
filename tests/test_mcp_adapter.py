from pathlib import Path

import yaml

from projectctl.adapters.mcp import McpToolAdapter
from projectctl.project import Project
from projectctl.scaffold import install_scaffold
from projectctl.service import ProjectService


EXPECTED_TOOLS = {
    "get_status",
    "get_next_task",
    "build_context",
    "claim_task",
    "submit_result",
    "submit_review",
    "submit_qa",
    "record_test_result",
    "evaluate_task",
}


def _adapter(tmp_path: Path) -> McpToolAdapter:
    install_scaffold(tmp_path, project_id="demo", project_name="Demo")
    backlog = tmp_path / ".project-os/state/backlog.yaml"
    backlog.write_text(
        yaml.safe_dump({
            "tasks": [{
                "id": "TASK-1",
                "title": "Implement",
                "role": "developer",
                "priority": "P0",
                "status": "ready",
                "acceptance": ["works"],
            }]
        }, sort_keys=False),
        encoding="utf-8",
    )
    return McpToolAdapter(ProjectService(Project(tmp_path)))


def test_mcp_surface_exposes_only_business_intent_tools(tmp_path: Path):
    adapter = _adapter(tmp_path)

    tools = adapter.list_tools()
    names = {tool["name"] for tool in tools}

    assert names == EXPECTED_TOOLS
    assert all("inputSchema" in tool for tool in tools)
    assert not any(
        token in name
        for name in names
        for token in ("yaml", "file_write", "write_file", "mutate_state")
    )


def test_mcp_adapter_uses_same_harness_result_as_service(tmp_path: Path):
    adapter = _adapter(tmp_path)

    result = adapter.call_tool("get_status", {})

    assert result["version"] == 1
    assert result["ok"] is True
    assert result["action"] == "get_status"
    assert result["data"]["project_id"] == "demo"


def test_mcp_claim_routes_through_canonical_state_writer(tmp_path: Path):
    adapter = _adapter(tmp_path)

    result = adapter.call_tool(
        "claim_task",
        {"task_id": "TASK-1", "role": "developer"},
    )

    assert result["ok"] is True
    project = adapter.service.project
    assert project.backlog()["tasks"][0]["status"] == "active"
    assert project.current_state()["current_tasks"] == ["TASK-1"]


def test_mcp_unknown_tool_returns_structured_error(tmp_path: Path):
    adapter = _adapter(tmp_path)

    result = adapter.call_tool("write_yaml", {"path": "x"})

    assert result["ok"] is False
    assert result["error"]["code"] == "unknown_tool"


def test_mcp_invalid_arguments_do_not_escape_as_raw_exception(tmp_path: Path):
    adapter = _adapter(tmp_path)

    result = adapter.call_tool("build_context", {})

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_request"
