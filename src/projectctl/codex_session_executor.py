from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .codex_cli import parse_thread_started, spawn_exec, stdout_lines
from .control_service import CentralControlService


SpawnCodex = Callable[..., Any]


class CodexSessionExecutor:
    """Execute one remote job while Project OS owns the persistent Codex session."""

    def __init__(
        self,
        control: CentralControlService,
        *,
        spawner: SpawnCodex = spawn_exec,
    ):
        self.control = control
        self.spawner = spawner

    def execute(
        self,
        project_id: str,
        job_id: str,
        prompt: str,
        *,
        source: str = "telegram",
        worker_id: str | None = None,
        cwd: Path | str | None = None,
        codex_bin: str | None = None,
        extra_args: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        ticket = self.control.begin_session_job(
            project_id,
            job_id,
            source=source,
            worker_id=worker_id,
            prompt_preview=prompt,
        )
        recovered = False

        for attempt in range(2):
            job = ticket["job"]
            codex_session_id = job.get("codex_session_id")
            mode = str(job["execution_mode"])
            lines: list[str] = []
            thread_id: str | None = None

            try:
                process = self.spawner(
                    prompt,
                    codex_session_id=codex_session_id,
                    codex_bin=codex_bin,
                    extra_args=extra_args,
                    cwd=cwd,
                )
            except OSError:
                if mode == "resumed_session" and attempt == 0:
                    self.control.finish_session_job(
                        job_id,
                        success=False,
                        error_code="CODEX_RESUME_FAILED",
                        session_fatal=True,
                    )
                    ticket = self.control.recover_session_job(
                        job_id,
                        created_by=source,
                        worker_id=worker_id,
                    )
                    recovered = True
                    continue
                self.control.finish_session_job(
                    job_id,
                    success=False,
                    error_code="CODEX_START_FAILED",
                    session_fatal=True,
                )
                raise

            for raw_line in stdout_lines(process):
                line = raw_line.rstrip("\r\n")
                lines.append(line)
                candidate = parse_thread_started(line)
                if not candidate or thread_id is not None:
                    continue
                thread_id = candidate
                binding = self.control.bind_session_thread(job_id, candidate)
                if not binding["matched"]:
                    process.terminate()
                    process.wait()
                    if attempt == 0:
                        ticket = self.control.recover_session_job(
                            job_id,
                            created_by=source,
                            worker_id=worker_id,
                        )
                        recovered = True
                        break
                    return {
                        "ok": False,
                        "job_id": job_id,
                        "error_code": "SESSION_NOT_FOUND",
                        "lines": lines,
                        "recovered": recovered,
                    }
            else:
                return_code = int(process.wait())
                if return_code == 0 and thread_id:
                    completed = self.control.finish_session_job(job_id)
                    return {
                        "ok": True,
                        "job_id": job_id,
                        "project_id": project_id,
                        "session_id": completed["session"]["session_id"],
                        "codex_session_id": completed["session"]["codex_session_id"],
                        "execution_mode": completed["job"]["execution_mode"],
                        "lines": lines,
                        "recovered": recovered,
                    }

                error_code = (
                    "CODEX_RESUME_FAILED"
                    if mode == "resumed_session"
                    else "CODEX_START_FAILED"
                )
                self.control.finish_session_job(
                    job_id,
                    success=False,
                    error_code=error_code,
                    session_fatal=True,
                )
                if mode == "resumed_session" and attempt == 0:
                    ticket = self.control.recover_session_job(
                        job_id,
                        created_by=source,
                        worker_id=worker_id,
                    )
                    recovered = True
                    continue
                return {
                    "ok": False,
                    "job_id": job_id,
                    "error_code": error_code,
                    "return_code": return_code,
                    "lines": lines,
                    "recovered": recovered,
                }

            # A resume mismatch breaks out of the stdout loop after terminating.
            if ticket["job"]["execution_mode"] == "new_session":
                continue

        return {
            "ok": False,
            "job_id": job_id,
            "error_code": "CODEX_START_FAILED",
            "recovered": recovered,
        }
