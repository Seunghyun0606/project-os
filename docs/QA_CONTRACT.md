# Codex 자동 QA Contract

## 1. 개요

Project OS의 QA 기능은 테스트 runner가 아니라 프로젝트 간 공통 인터페이스입니다.

    Project OS
      ↓
    QA Contract / optional Scaffold
      ↓
    Actual Project
      ↓
    project-specific QA implementation
      ↓
    Remote Control

Project OS는 scripts/qa.ps1, .qa/runs/<run-id>/result.json, artifact metadata의 형태만 정의합니다. 실제 build/test/UI automation은 각 프로젝트가 구현합니다.

Project OS가 직접 구현하지 않는 것:

- Playwright
- Godot 실행/테스트
- Android ADB/Appium
- pytest
- Electron/Tauri test
- Codex process spawning
- Telegram/Remote Control worker
- Human Gate UI
- screenshot 전송
- 별도 QA 서버/중앙 Dashboard

## 2. 왜 QA Contract가 필요한가

프로젝트마다 테스트 기술은 달라도 Codex와 Remote Control이 알아야 할 질문은 같습니다.

- QA를 어떻게 시작하는가?
- 자동 검증이 성공했는가?
- 어떤 단계가 실행됐고 어떤 단계가 생략됐는가?
- 실패가 테스트 실패인지 환경 문제인지?
- 사람이 봐야 할 UI artifact가 있는가?
- artifact 파일은 어디에 있는가?

이 정보를 하나의 contract로 고정하면 Remote Control은 Web/Godot/Android의 내부 구현을 알 필요가 없습니다.

## 3. Quick Start

새 프로젝트에서 기본 Project OS만 설치:

    projectctl init

QA도 처음부터 사용할 프로젝트:

    projectctl init --with-qa

이미 Project OS를 사용하는 프로젝트에는 기존 scaffold를 덮어쓰지 않고 QA overlay만 설치합니다.

    projectctl qa-init

생성되는 QA 파일:

    scripts/
      qa.ps1

    qa/
      README.md
      result.example.json
      scenarios/
        smoke.example.yaml

    .qa/
      .gitignore
      .gitkeep

.qa/runs/는 실행 시 생성되는 runtime artifact 영역이며 기본적으로 Git에서 제외합니다.

초기 qa.ps1은 QA가 구현된 것처럼 거짓 성공하지 않습니다. QA_NOT_CONFIGURED 오류가 포함된 FAIL result를 만들고 exit code 1로 종료합니다.

## 4. 프로젝트에서 qa.ps1 구현하기

Windows 우선 공통 entry point:

    .\scripts\qa.ps1

외부 호출자는 deterministic한 run id를 넘길 수 있습니다.

    .\scripts\qa.ps1 -RunId QA-20260928-001

권장 실행 순서:

    preflight
    → build
    → launch
    → smoke test
    → functional test
    → optional UI scenario
    → artifact collection
    → result.json 생성
    → process cleanup

모든 프로젝트가 모든 단계를 구현할 필요는 없습니다. 지원하지 않는 단계는 SKIPPED로 기록합니다.

공통 규칙:

1. 가능한 한 항상 result.json을 생성합니다.
2. 실행되지 못한 테스트를 PASS로 기록하지 않습니다.
3. 프로젝트가 시작한 child process는 cleanup 단계에서 종료합니다.
4. 원본 framework report를 남겨도 되지만 Remote Control은 공통 result.json만으로 상태를 판단할 수 있어야 합니다.
5. PowerShell 5.1에서도 동작할 수 있도록 보수적인 문법을 사용합니다.

공통 exit code:

| Exit code | 의미 |
| --- | --- |
| 0 | PASS |
| 1 | FAIL |
| 2 | UI_REVIEW_REQUIRED |

## 5. result.json 규격

Schema 파일:

    schemas/qa-result.schema.json

Contract version은 1.0입니다.

run-level status:

- PASS
- FAIL
- UI_REVIEW_REQUIRED

자동 stage status:

- PASS
- FAIL
- SKIPPED

UI stage는 추가로 REVIEW_REQUIRED를 사용할 수 있습니다.

예:

    {
      "schema_version": "1.0",
      "run_id": "QA-example-001",
      "project": "desktown",
      "status": "UI_REVIEW_REQUIRED",
      "started_at": "2026-09-28T01:00:00Z",
      "finished_at": "2026-09-28T01:02:00Z",
      "preflight": "PASS",
      "build": "PASS",
      "launch": "PASS",
      "smoke": "PASS",
      "functional": "PASS",
      "ui": "REVIEW_REQUIRED",
      "artifact_collection": "PASS",
      "cleanup": "PASS",
      "next_action": "REQUEST_UI_REVIEW",
      "errors": [],
      "artifacts": []
    }

UI_APPROVED와 UI_REJECTED는 QA runner 결과가 아닙니다.

    QA runner
      UI_REVIEW_REQUIRED
            ↓
    Remote Control / Human Gate
            ↓
      UI_APPROVED 또는 UI_REJECTED

QA schema는 두 Human Gate 상태를 의도적으로 허용하지 않습니다.

환경 문제로 QA가 실행되지 못한 경우 PASS가 아닙니다. FAIL과 kind=environment, next_action=INVESTIGATE_ENVIRONMENT 조합을 사용합니다.

## 6. Artifact 규격

기본 run directory:

    .qa/
      runs/
        <run-id>/
          result.json
          stdout.log
          stderr.log
          screenshots/
          videos/
          artifacts/

지원 artifact type:

- screenshot
- video
- log
- report
- trace
- other

예:

    {
      "type": "screenshot",
      "name": "main-screen",
      "path": "screenshots/01-main.png",
      "scenario": "main-flow"
    }

path는 반드시 QA run directory 기준의 forward-slash relative path입니다.

허용:

    screenshots/01-main.png
    artifacts/junit.xml
    stdout.log

허용하지 않음:

    C:\temp\screen.png
    /tmp/screen.png
    ../other-run/result.json
    screenshots/../secret.png

## 7. Codex 작업과 연결

consumer scaffold의 AGENTS.md는 scripts/qa.ps1이 존재하는 경우 완료 전에 QA를 실행하도록 규정합니다.

Codex completion rule:

1. implementation 완료 후 QA entry point가 있으면 실행합니다.
2. FAIL이면 완료 처리하지 않고 원인을 분석합니다.
3. 수정 가능한 실패는 합리적인 횟수 안에서 수정 후 다시 실행합니다.
4. functional 자동 검증이 통과했지만 시각 판단이 필요하면 UI_REVIEW_REQUIRED를 유지합니다.
5. 작업 결과에 QA run id, status, result.json과 artifact 위치를 기록합니다.
6. 환경 문제로 실행하지 못한 경우 성공으로 간주하지 않습니다.
7. 최종 UI 미감 승인과 UI_APPROVED/UI_REJECTED 결정은 Codex가 하지 않습니다.

## 8. Remote Control과 연결

Remote Control이 알아야 하는 interface는 다음뿐입니다.

1. entry point 존재 여부: scripts/qa.ps1
2. run id 전달: -RunId QA-...
3. result 위치: .qa/runs/<run-id>/result.json
4. result schema: 1.0
5. artifact path 기준: result가 있는 run directory
6. exit code: 0=PASS, 1=FAIL, 2=UI_REVIEW_REQUIRED

권장 흐름:

    Remote Control
        ↓
    scripts/qa.ps1 -RunId <known-id>
        ↓
    exit code + result.json
        ↓
    schema/status 확인
        ↓
    artifacts[] resolve
        ↓
    PASS / FAIL / UI review 요청

Remote Control은 프로젝트가 Playwright인지 Godot인지 Android인지 검사할 필요가 없습니다.

entry point가 없다면 QA unsupported라는 사실만 알 수 있습니다. 이를 자동으로 PASS로 바꾸는 것은 Remote Control 정책의 책임이며 Project OS contract는 그렇게 판단하지 않습니다.

## 9. 프로젝트 종류별 예시

### Web

    preflight  → Node/browser 확인
    build      → 프로젝트 build
    launch     → dev/test server
    smoke      → HTTP health + browser load
    functional → 프로젝트가 선택한 browser test
    ui         → screenshot 후 필요 시 REVIEW_REQUIRED
    cleanup    → server/browser 종료

Project OS는 Playwright dependency나 test code를 제공하지 않습니다.

### Godot

    preflight  → Godot executable/project 확인
    build      → export/build 또는 SKIPPED
    launch     → game 실행
    smoke      → startup/crash 검사
    functional → project-specific scene/test harness
    ui         → 주요 scene capture
    cleanup    → game process 종료

Project OS는 Godot binary나 scene test framework를 제공하지 않습니다.

### Android

    preflight  → JDK/SDK/device 또는 emulator 확인
    build      → Gradle build
    launch     → install + activity launch
    smoke      → crash/startup 검사
    functional → project-specific instrumentation/UI test
    ui         → screenshot/video
    cleanup    → test process/app 정리

Project OS는 ADB/Appium/emulator lifecycle을 구현하지 않습니다.

## 10. Troubleshooting

### qa.ps1이 항상 FAIL

새 scaffold의 기본 동작입니다. QA_NOT_CONFIGURED이면 프로젝트에 맞는 QA 구현을 추가해야 합니다.

### 테스트 도구가 없어 실행 불가

PASS로 바꾸지 않습니다. FAIL + kind=environment + next_action=INVESTIGATE_ENVIRONMENT를 사용합니다.

### 일부 단계가 프로젝트에 없음

SKIPPED를 사용합니다. 존재하지 않는 기능을 억지로 구현할 필요는 없습니다.

### 자동 테스트는 통과했는데 화면을 사람이 봐야 함

run status를 UI_REVIEW_REQUIRED, UI stage를 REVIEW_REQUIRED, next action을 REQUEST_UI_REVIEW로 기록하고 screenshot/video artifact를 남깁니다.

### Remote Control이 artifact를 못 찾음

artifact path가 절대경로 또는 repository 기준 경로인지 확인합니다. 반드시 .qa/runs/<run-id>/ 기준 상대경로여야 합니다.

### 기존 프로젝트에 QA만 추가하고 싶음

projectctl init --force를 사용하지 않습니다. 기존 Project OS 파일을 건드리지 않는 projectctl qa-init을 사용합니다.
