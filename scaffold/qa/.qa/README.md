# Project QA Scaffold

This directory is the Project OS QA Contract v2 consumer overlay.

Project OS defines only the interface. The project chooses and implements its own test tools.

- `manifest.yaml`: discovery point for Remote Control and other callers.
- `scenarios/*.yaml`: semantic scenarios interpreted by the project runner.
- `scripts/run-qa.ps1`: Windows entry point template.
- `scripts/run-qa.sh`: Unix entry point template.
- `result.example.json`: QA Result Contract v2 example.
- `runs/`: runtime output, ignored by Git.

Replace the template runner with project-specific build/test/UI logic, but keep the manifest and result contract stable. The runner should accept a caller-provided run id, emit `result.json` even on failures when possible, and store artifacts using repository-relative forward-slash paths.

Result JSON is the source of truth. Exit codes are transport hints: 0=PASS/PASS_WITH_WARNINGS, 1=FAIL, 2=HUMAN_GATE_REQUIRED.

The scaffold intentionally returns `FAIL` / `QA_NOT_CONFIGURED` until project-specific QA is implemented.
