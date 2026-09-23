import json

from projectctl.codex_cli import (
    build_attach_args,
    build_exec_args,
    codex_child_env,
    first_thread_started,
    parse_thread_started,
    resolved_codex_home,
)


CODEX_ID = "019f1234-aaaa-bbbb-cccc-1234567890ab"


def test_build_exec_args_starts_new_session_without_shell_string():
    args = build_exec_args(
        "다음 작업 진행해줘",
        codex_bin="codex",
        extra_args=["--skip-git-repo-check"],
    )

    assert args == [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--",
        "다음 작업 진행해줘",
    ]


def test_build_exec_args_resumes_existing_session():
    args = build_exec_args(
        "테스트도 돌려줘",
        codex_session_id=CODEX_ID,
        codex_bin="codex",
    )

    assert args[:4] == ["codex", "exec", "resume", CODEX_ID]
    assert "--json" in args
    assert args[-2:] == ["--", "테스트도 돌려줘"]


def test_thread_started_parser_extracts_codex_session_id():
    line = json.dumps({"type": "thread.started", "thread_id": CODEX_ID})

    assert parse_thread_started(line) == CODEX_ID
    assert first_thread_started([
        json.dumps({"type": "turn.started"}),
        line,
        json.dumps({"type": "turn.completed"}),
    ]) == CODEX_ID


def test_thread_started_parser_ignores_non_json_and_other_events():
    assert parse_thread_started("not-json") is None
    assert parse_thread_started('{"type":"turn.started"}') is None


def test_codex_home_prefers_project_os_override():
    env = {
        "PROJECT_OS_CODEX_HOME": "/shared/project-os-codex",
        "CODEX_HOME": "/other/codex",
        "PATH": "/bin",
    }

    assert str(resolved_codex_home(env)) == "/shared/project-os-codex"
    child = codex_child_env(env)
    assert child["CODEX_HOME"] == "/shared/project-os-codex"


def test_attach_targets_non_interactive_exec_session_by_id():
    assert build_attach_args(CODEX_ID) == [
        "codex",
        "resume",
        "--include-non-interactive",
        CODEX_ID,
    ]
