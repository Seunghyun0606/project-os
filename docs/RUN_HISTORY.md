# Run history compaction

Project OS keeps canonical project direction and task state separate from runtime history.

Runtime records may be written under:

\`.project-os/runs/history/\`

A run record is structured YAML or JSON and should include a stable \`run_id\`. ISO-8601 timestamps are recommended so recent-run retention behaves as expected.

Example:

\`\`\`yaml
run_id: RUN-20260923-001
task: TASK-001
role: developer
status: completed
started_at: 2026-09-23T10:00:00Z
finished_at: 2026-09-23T10:12:00Z
summary: Added deterministic dependency validation.
artifacts:
  - src/projectctl/doctor.py
evidence:
  - pytest passed
usage:
  input_tokens: 12000
  output_tokens: 1800
events:
  - type: tool
  - type: result
\`\`\`

## Compaction

Run:

\`\`\`bash
projectctl compact-runs --keep-recent 20
\`\`\`

The command:

1. reads all structured run files before changing anything,
2. sorts runs deterministically by timestamp, run id and path,
3. keeps the newest requested number in \`runs/history/\`,
4. writes compact metadata to \`runs/summaries/history.yaml\`,
5. moves older raw records to \`runs/archive/\`.

Raw history is archived rather than deleted. This keeps normal context retrieval small while retaining recoverable evidence in Git.

Compaction does not ask an LLM to summarize history. It preserves explicitly supplied run summaries and compact structured metadata such as status, artifacts, evidence, usage and event counts.

If an archive destination already exists with different content, or duplicate run ids are found, the command stops before writing the summary or moving any source files.
