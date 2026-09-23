# Multi-harness integration

Project OS Phase 5 exposes the same deterministic core to CLI, MCP-style tools and future harnesses.

The important boundary is:

```text
CLI ---------\
              \
MCP adapter ---> ProjectService ---> deterministic Project OS core
              /
future harness/
```

Harness adapters do not reimplement scheduling, context selection, permissions, quality gates or canonical state transitions.

## ProjectService

`ProjectService` is the harness-neutral application API.

It exposes business intent rather than file mutation:

- get_status
- get_next_task
- build_context
- claim_task
- submit_result
- submit_review
- submit_qa
- record_test_result
- evaluate_task

Every call returns the same versioned envelope:

```json
{
  "version": 1,
  "ok": true,
  "action": "get_status",
  "data": {},
  "error": null
}
```

Failures are also structured:

```json
{
  "version": 1,
  "ok": false,
  "action": "claim_task",
  "data": null,
  "error": {
    "code": "invalid_request",
    "message": "..."
  }
}
```

The schema is stored in `schemas/harness-result.schema.json`.

## CLI

The existing CLI remains the primary local interface.

Core commands such as status, next, context, claim, submit, review, QA, test recording and evaluation now call `ProjectService` rather than maintaining a separate business implementation.

Example:

```bash
projectctl next --role developer
projectctl claim TASK-001 --role developer
projectctl submit TASK-001 result.yaml --actor dev-1
projectctl record-test TASK-001 tests.yaml --actor ci
projectctl review TASK-001 review.yaml --actor reviewer-1
projectctl evaluate TASK-001 evaluation.yaml --actor evaluator-1
```

## MCP adapter

`projectctl.adapters.mcp.McpToolAdapter` exposes a small MCP-compatible business tool catalog and dispatches each call to `ProjectService`.

It intentionally does not expose tools such as:

- write_yaml
- write_file
- mutate_state
- arbitrary repository write

This preserves the Project OS permission and single-writer rules.

The adapter itself does not add an MCP transport/server dependency. A real MCP host can register the tool descriptors and forward tool calls to this adapter. This keeps the Project OS package usable in closed or minimal environments without requiring an MCP SDK.

Example integration shape:

```python
from projectctl.adapters.mcp import McpToolAdapter
from projectctl.service import ProjectService

adapter = McpToolAdapter(ProjectService.open())

tools = adapter.list_tools()
result = adapter.call_tool(
    "get_next_task",
    {"role": "developer"},
)
```

If a specific MCP SDK is adopted later, its server/transport code should stay thin and call this adapter or `ProjectService`.

## Automated test evidence

Automated verification is recorded separately from implementation output:

```text
TASK-001.yaml        implementation handoff
TASK-001.tests.yaml  automated test evidence
TASK-001.review.yaml independent review
TASK-001.qa.yaml     QA handoff
TASK-001.evaluation.yaml
```

This prevents a harness from rewriting an implementation result merely to attach later CI evidence.

When quality gates such as build, lint, typecheck, unit_test or integration_test are configured, `QualityGateEvaluator` combines implementation verification with the separate test evidence. Explicit test evidence takes precedence for matching automated gates.

## Adapter requirements

Any future Cursor, Claude Code, Codex, HTTP or central-service adapter should:

1. call `ProjectService` instead of rewriting business rules,
2. use the versioned harness result envelope,
3. expose business-intent operations rather than raw state mutation,
4. preserve actor identity for handoffs,
5. leave canonical state transitions to the existing validated path.
