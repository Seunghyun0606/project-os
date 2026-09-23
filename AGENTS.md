# Project OS Repository Instructions

This repository develops Project OS itself.

## Scope boundaries

- `scaffold/default/` is the only content copied into consumer projects.
- `src/`, `defaults/`, `schemas/`, `docs/`, `tests/`, root version files and CI are Project OS development files.
- Remote execution, messenger network gateways, host routing and Lightsail/Desktop machine control are out of scope here. Cross-channel Project Session identity/persistence/locking and Codex thread binding are control-plane concerns and may be implemented here behind transport-neutral services.

## Development rules

1. Preserve separation between consumer scaffold and Project OS implementation.
2. Keep Project OS model/provider agnostic.
3. Prefer deterministic code for dependency, state and validation logic.
4. Do not make an LLM responsible for canonical state transitions that code can validate.
5. Do not let worker agents approve their own work.
6. Keep canonical project memory in Git-managed project files.
7. Add migrations for breaking schema changes; never overwrite consumer project state during upgrades.
8. Run tests and `projectctl doctor` against a generated scaffold before marking work complete.
