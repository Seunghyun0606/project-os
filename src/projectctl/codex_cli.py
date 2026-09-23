from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import IO

from .sessions import validate_codex_session_id


class CodexCliError(RuntimeError):
    pass


def resolved_codex_home(env: Mapping[str, str] | None = None) -> Path | None:
    source = os.environ if env is None else env
    raw = source.get("PROJECT_OS_CODEX_HOME") or source.get("CODEX_HOME")
    if not raw:
        return None
    return Path(raw).expanduser()


def codex_child_env(env: Mapping[str, str] | None = None) -> dict[str, str]:
    child = dict(os.environ if env is None else env)
    home = resolved_codex_home(child)
    if home is not None:
        child["CODEX_HOME"] = str(home)
    return child


def resolve_codex_executable(
    explicit: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    if explicit:
        return explicit

    source = os.environ if env is None else env
    path = source.get("PATH")
    candidates = ("codex.cmd", "codex") if os.name == "nt" else ("codex",)
    for candidate in candidates:
        found = shutil.which(candidate, path=path)
        if found:
            return found
    raise FileNotFoundError(
        "Codex CLI was not found on PATH. Set PROJECT_OS_CODEX_BIN or install codex."
    )


def configured_codex_executable(
    explicit: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    source = os.environ if env is None else env
    return resolve_codex_executable(
        explicit or source.get("PROJECT_OS_CODEX_BIN"),
        env=source,
    )


def build_exec_args(
    prompt: str,
    *,
    codex_session_id: str | None = None,
    codex_bin: str = "codex",
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("prompt must be a non-empty string")

    args = [codex_bin, "exec"]
    if codex_session_id:
        args.extend(["resume", validate_codex_session_id(codex_session_id)])
    args.append("--json")
    if extra_args:
        args.extend(str(item) for item in extra_args)
    args.extend(["--", prompt])
    return args


def build_attach_args(
    codex_session_id: str,
    *,
    codex_bin: str = "codex",
    include_non_interactive: bool = True,
) -> list[str]:
    args = [codex_bin, "resume"]
    if include_non_interactive:
        args.append("--include-non-interactive")
    args.append(validate_codex_session_id(codex_session_id))
    return args


def parse_thread_started(line: str) -> str | None:
    try:
        payload = json.loads(line)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("type") != "thread.started":
        return None
    thread_id = payload.get("thread_id")
    if not isinstance(thread_id, str):
        raise CodexCliError("thread.started event did not contain thread_id")
    return validate_codex_session_id(thread_id)


def first_thread_started(lines: Iterable[str]) -> str | None:
    for line in lines:
        thread_id = parse_thread_started(line)
        if thread_id:
            return thread_id
    return None


def spawn_exec(
    prompt: str,
    *,
    codex_session_id: str | None = None,
    codex_bin: str | None = None,
    extra_args: Sequence[str] | None = None,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.Popen[str]:
    child_env = codex_child_env(env)
    executable = configured_codex_executable(codex_bin, env=child_env)
    args = build_exec_args(
        prompt,
        codex_session_id=codex_session_id,
        codex_bin=executable,
        extra_args=extra_args,
    )
    return subprocess.Popen(
        args,
        cwd=None if cwd is None else str(cwd),
        env=child_env,
        shell=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def stdout_lines(process: subprocess.Popen[str]) -> IO[str]:
    if process.stdout is None:
        raise CodexCliError("Codex process stdout is not captured")
    return process.stdout


def run_attach(
    codex_session_id: str,
    *,
    codex_bin: str | None = None,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    include_non_interactive: bool = True,
) -> int:
    child_env = codex_child_env(env)
    executable = configured_codex_executable(codex_bin, env=child_env)
    args = build_attach_args(
        codex_session_id,
        codex_bin=executable,
        include_non_interactive=include_non_interactive,
    )
    completed = subprocess.run(
        args,
        cwd=None if cwd is None else str(cwd),
        env=child_env,
        shell=False,
        check=False,
    )
    return int(completed.returncode)
