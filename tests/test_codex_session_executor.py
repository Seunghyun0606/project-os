import io
import json
from pathlib import Path

from projectctl.central_store import CentralControlStore
from projectctl.codex_session_executor import CodexSessionExecutor
from projectctl.control_service import CentralControlService


THREAD_A = "019f1111-aaaa-bbbb-cccc-1234567890ab"
THREAD_B = "019f2222-aaaa-bbbb-cccc-1234567890ab"
THREAD_C = "019f3333-aaaa-bbbb-cccc-1234567890ab"


def _register(store: CentralControlStore, tmp_path: Path) -> None:
    store.upsert_project({
        "project_id": "project-os",
        "project_name": "Project OS",
        "root_path": str(tmp_path / "project-os"),
        "project_status": "active",
        "current_milestone": None,
        "human_gate": False,
        "scaffold_version": "0.2.0",
        "schema_version": "1",
        "package_compatibility": ">=0.2,<1.0",
        "compatibility_status": "compatible",
        "compatibility_reason": "ok",
    })


class FakeProcess:
    def __init__(self, thread_id: str, return_code: int = 0):
        payloads = [
            json.dumps({"type": "thread.started", "thread_id": thread_id}),
            json.dumps({"type": "turn.started"}),
            json.dumps({"type": "turn.completed"}),
        ]
        self.stdout = io.StringIO("\n".join(payloads) + "\n")
        self.return_code = return_code
        self.terminated = False

    def wait(self):
        return self.return_code

    def terminate(self):
        self.terminated = True


def test_executor_creates_then_resumes_same_codex_thread(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path)
    control = CentralControlService(store)
    calls = []

    def spawn(prompt, **kwargs):
        calls.append(kwargs.get("codex_session_id"))
        return FakeProcess(THREAD_A)

    executor = CodexSessionExecutor(control, spawner=spawn)

    first = executor.execute("project-os", "JOB-001", "현재 코드 확인해줘")
    second = executor.execute("project-os", "JOB-002", "다음 작업 진행해줘")

    assert first["ok"] is True
    assert first["execution_mode"] == "new_session"
    assert second["ok"] is True
    assert second["execution_mode"] == "resumed_session"
    assert first["session_id"] == second["session_id"]
    assert second["codex_session_id"] == THREAD_A
    assert calls == [None, THREAD_A]


def test_executor_detects_silent_resume_replacement_and_recovers_once(tmp_path: Path):
    store = CentralControlStore(tmp_path / "control.db")
    _register(store, tmp_path)
    control = CentralControlService(store)

    seed_calls = []

    def seed_spawn(prompt, **kwargs):
        seed_calls.append(kwargs.get("codex_session_id"))
        return FakeProcess(THREAD_A)

    CodexSessionExecutor(control, spawner=seed_spawn).execute(
        "project-os",
        "JOB-001",
        "seed",
    )

    processes = []
    calls = []

    def recovering_spawn(prompt, **kwargs):
        calls.append(kwargs.get("codex_session_id"))
        thread = THREAD_B if len(calls) == 1 else THREAD_C
        process = FakeProcess(thread)
        processes.append(process)
        return process

    result = CodexSessionExecutor(control, spawner=recovering_spawn).execute(
        "project-os",
        "JOB-002",
        "continue",
    )

    assert calls == [THREAD_A, None]
    assert processes[0].terminated is True
    assert result["ok"] is True
    assert result["recovered"] is True
    assert result["execution_mode"] == "new_session"
    assert result["codex_session_id"] == THREAD_C
    sessions = control.list_sessions("project-os")
    assert len(sessions) == 2
    assert {item["status"] for item in sessions} == {"error", "idle"}
