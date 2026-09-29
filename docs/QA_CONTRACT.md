# Automated QA Contract v2

## 1. 개요

Project OS의 Automated QA는 테스트 엔진이 아니라 **프로젝트 간 공통 Contract**입니다.

```text
Project OS
    ↓
QA Contract / Scaffold

각 Project
    ↓
project-specific QA Runner
    ↓
result.json + artifacts

Remote Control
    ↓
manifest + result.json 해석
    ↓
외부 알림 / Job Status / Human Gate
```

Project OS가 소유하는 것은 Manifest, Scenario, Result, Artifact, Screenshot, Visual Review의 형식뿐입니다. Playwright, Android Emulator, Godot, Chromium, Windows app automation 같은 실제 실행 기술은 각 프로젝트가 선택합니다.

Project OS에는 다음을 구현하지 않습니다.

- Telegram API/Bot
- Remote Control Job orchestration
- Runner/Host 관리
- Codex/Claude provider orchestration
- 특정 프로젝트 전용 QA 코드
- 특정 테스트 프레임워크의 강제 dependency

## 2. Quick Start

새 프로젝트에 base scaffold와 QA를 함께 설치:

```bash
projectctl init --with-qa
```

이미 Project OS를 사용하는 프로젝트에 QA overlay만 설치:

```bash
projectctl qa-init
```

생성 구조:

```text
.qa/
├─ manifest.yaml
├─ README.md
├─ result.example.json
├─ scenarios/
│  └─ example.yaml
├─ scripts/
│  ├─ run-qa.ps1
│  └─ run-qa.sh
└─ runs/                 # runtime output, Git ignored
```

기본 runner는 거짓 PASS를 만들지 않습니다. 프로젝트별 QA를 구현하기 전에는 `QA_NOT_CONFIGURED` 오류와 `FAIL` result를 남깁니다.

## 3. QA Manifest

Discovery point는 항상 다음입니다.

```text
.qa/manifest.yaml
```

예:

```yaml
schemaVersion: "2.0"

qa:
  command:
    windows: "powershell -NoProfile -ExecutionPolicy Bypass -File .qa/scripts/run-qa.ps1 -RunId {runId}"
    unix: "./.qa/scripts/run-qa.sh --run-id {runId}"
  stages:
    - build
    - unit
    - integration
    - smoke
    - ui
    - visual
  timeoutSeconds: 900
  environment:
    required: []
    optional: []

scenarios:
  directory: ".qa/scenarios"

artifacts:
  result: ".qa/runs/{runId}/result.json"
  screenshots: ".qa/runs/{runId}/screenshots"
  logs: ".qa/runs/{runId}/logs"
  visual: ".qa/runs/{runId}/visual"
  metadata: ".qa/runs/{runId}/metadata"
```

Manifest가 표현하는 정보:

- host OS별 QA 실행 command
- 프로젝트가 지원하는 stage
- result/screenshot/log/visual/metadata 위치
- optional timeout
- optional environment requirements
- scenario directory

`{runId}`는 외부 caller가 생성한 안전한 run id로 치환합니다.

Schema:

```text
schemas/qa-manifest.schema.json
```

## 4. QA Scenario

Scenario는 실행 엔진 DSL이 아니라 **의미적 Contract**입니다. `launch_app`, `start_focus`, `mina_visible` 같은 의미를 실제로 어떻게 수행하는지는 프로젝트 runner가 결정합니다.

예:

```yaml
schemaVersion: "2.0"
id: companion_focus_session
name: Companion Focus Session
type: ui
required: true
timeoutSeconds: 120
tags: [smoke, ui]
humanGate: false

steps:
  - action: launch_app
  - waitFor: main_window_ready
  - screenshot: 01-main
    caption: Main window after launch
  - action: start_focus
  - screenshot: 02-focus-running
    caption: Focus session running

assertions:
  - app_running
  - mina_visible
  - timer_running
```

지원 항목:

- scenario id / name / type
- semantic steps
- assertions
- screenshot checkpoints
- tags
- timeout
- required/optional
- humanGate

Schema:

```text
schemas/qa-scenario.schema.json
```

## 5. QA Runner

Runner는 프로젝트가 구현합니다. Project OS는 runner 내부 기술을 알지 못합니다.

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .qa/scripts/run-qa.ps1 -RunId QA-20260929-001
```

Unix:

```bash
./.qa/scripts/run-qa.sh --run-id QA-20260929-001
```

Runner 규칙:

1. caller가 준 run id를 사용합니다.
2. 지원하는 stage만 실행하고 미지원 stage/scenario는 `SKIPPED`로 기록할 수 있습니다.
3. 실패하더라도 가능한 경우 항상 유효한 `result.json`을 남깁니다.
4. 실행되지 않은 검증을 PASS로 기록하지 않습니다.
5. 프로젝트가 시작한 child process는 runner가 정리합니다.
6. 원본 framework report가 있더라도 공통 result만으로 외부 caller가 상태를 판단할 수 있어야 합니다.

Exit code는 transport hint입니다.

| Exit | 의미 |
| --- | --- |
| 0 | PASS 또는 PASS_WITH_WARNINGS |
| 1 | FAIL |
| 2 | HUMAN_GATE_REQUIRED |

최종 판단의 source of truth는 exit code가 아니라 `result.json.status`입니다.

## 6. QA Result

현재 Contract version은 `2.0`입니다.

Schema:

```text
schemas/qa-result.schema.json
```

최상위 status:

- `PASS`
- `PASS_WITH_WARNINGS`
- `FAIL`
- `HUMAN_GATE_REQUIRED`

stage status:

- `PENDING`
- `RUNNING`
- `PASS`
- `WARN`
- `FAIL`
- `SKIPPED`

기본 구조:

```json
{
  "schemaVersion": "2.0",
  "runId": "QA-20260929-001",
  "project": {"id": "desktown", "name": "DeskTown"},
  "status": "PASS_WITH_WARNINGS",
  "startedAt": "2026-09-29T12:00:00Z",
  "finishedAt": "2026-09-29T12:02:00Z",
  "summary": {
    "total": 20,
    "passed": 19,
    "failed": 0,
    "warnings": 1,
    "skipped": 0,
    "humanGates": 0
  },
  "stages": [],
  "scenarios": [],
  "artifacts": [],
  "visualReviews": [],
  "errors": [],
  "nextAction": "REVIEW_WARNINGS"
}
```

`HUMAN_GATE_REQUIRED`는 사람이 판단해야 할 지점이 존재한다는 QA 결과입니다. Human Gate 승인/거절 상태 자체는 Remote Control 등 외부 시스템의 책임이며 Project OS가 승인하지 않습니다.

## 7. Artifact Contract

Artifact path는 **repository/workspace root 기준 상대경로**이며 forward slash를 사용합니다.

허용:

```text
.qa/runs/QA-001/screenshots/01-main.png
.qa/runs/QA-001/logs/ui.log
.qa/runs/QA-001/visual/01-main-diff.png
```

금지:

```text
C:/temp/screen.png
/tmp/screen.png
../other-run/result.json
.qa/runs/x/../secret.png
.qa\runs\x\screen.png
```

Artifact type:

- screenshot
- visual_diff
- log
- report
- trace
- video
- metadata
- other

공통 metadata:

- name
- path
- stage
- scenarioId
- step
- caption
- severity
- createdAt
- mediaType
- sizeBytes
- sha256

절대경로를 Contract에 저장하지 않습니다.

## 8. Screenshot Contract

Screenshot은 1급 Artifact입니다.

Screenshot artifact에는 다음 필드를 사용합니다.

- `scenarioId`
- `step`
- `caption`
- `kind`
- `priority`

`kind`:

- initial
- checkpoint
- result
- failure
- visual_diff

`priority`:

- normal
- important
- failure

Remote Control은 이를 이용해 Telegram 등 외부 UI로 어떤 이미지를 보낼지 선택할 수 있습니다. Project OS에는 전송 로직을 넣지 않습니다.

권장 선택 정책 예:

```text
failure > important > normal
```

동일 priority에서는 `failure/result/checkpoint/initial` 같은 project policy를 외부에서 적용할 수 있습니다.

## 9. Visual QA Contract

Visual Review는 `visualReviews[]`에 기록합니다.

예:

```json
{
  "type": "visual_review",
  "status": "WARN",
  "scenarioId": "companion_focus_session",
  "artifact": ".qa/runs/QA-001/screenshots/02-focus-running.png",
  "issues": [
    {
      "severity": "warning",
      "category": "overlap",
      "message": "Character is too close to the bottom HUD.",
      "artifact": ".qa/runs/QA-001/screenshots/02-focus-running.png"
    }
  ]
}
```

category:

- clipping
- overlap
- alignment
- readability
- missing_asset
- unexpected_layout
- visual_regression
- hierarchy
- obstruction

누가 visual review를 수행하는지는 Contract 밖입니다. Project runner, Remote Control, 별도 AI reviewer 모두 가능하며 Project OS가 reviewer를 강제하지 않습니다.

## 10. Codex 작업 완료 규칙

consumer `AGENTS.md`는 `.qa/manifest.yaml`이 존재하면 QA-enabled project로 간주합니다.

코드 변경이 QA 대상이면:

```text
Implement
→ Build / project-specific checks
→ Automated QA
→ result.json
→ Artifact 저장
→ 작업 완료 판단
```

QA 없이 완료 처리할 수 있는 예외:

- 문서만 수정
- QA 환경 자체를 수정
- 실행 환경이 실제로 존재하지 않음
- Task가 명시적으로 QA 제외

예외를 사용한 경우 이유를 결과에 명시합니다.

`FAIL`은 완료가 아닙니다. `PASS_WITH_WARNINGS`는 warning/artifact를 함께 보고합니다. `HUMAN_GATE_REQUIRED`는 외부 사람 승인 전까지 그대로 유지합니다.

## 11. Remote Control Integration

Remote Control은 프로젝트 기술을 알아서는 안 됩니다.

권장 절차:

```text
1. repository root에서 .qa/manifest.yaml 탐색
2. manifest.schemaVersion 확인
3. host OS에 맞는 qa.command.windows 또는 qa.command.unix 선택
4. 안전한 runId 생성
5. command의 {runId} 치환
6. timeout 적용 후 command 실행
7. artifacts.result의 {runId} 치환
8. result.json 읽기
9. schemaVersion에 맞는 result schema로 validation
10. status / artifacts / visualReviews 해석
```

v2에서 Remote Control이 필요한 입력은 다음뿐입니다.

- `.qa/manifest.yaml`
- caller가 만든 `runId`
- manifest가 지정한 result path
- `schemas/qa-result.schema.json`의 v2 규격

상태 해석:

| Result | 외부 동작의 의미 |
| --- | --- |
| PASS | 자동 QA 통과 |
| PASS_WITH_WARNINGS | 통과했지만 warning/artifact를 노출 |
| FAIL | 실패 원인과 artifact를 노출하고 완료로 보지 않음 |
| HUMAN_GATE_REQUIRED | 외부 Human Gate를 생성하고 관련 screenshot/issue를 노출 |

Screenshot 전송 후보는 `artifacts[type=screenshot]`에서 `priority`와 `kind`를 이용해 선택합니다. Visual 문제는 `visualReviews[].issues`를 읽습니다.

Project OS에는 Telegram 전송 코드, Job 상태 변경 코드, Human Gate UI를 넣지 않습니다.

## 12. 프로젝트별 Adapter 예

### Web

- build: project build
- unit: Vitest/Jest 등
- integration/ui: Playwright 등
- screenshots: browser capture

### Android

- build: Gradle
- integration: instrumentation
- ui: Espresso/UIAutomator 등
- screenshots: device/emulator capture

### Godot / Windows

- build/export: project-specific command
- smoke: process launch/crash check
- integration: test hooks
- ui/visual: Windows capture

### Chrome Extension

- build: extension bundle
- integration/ui: Chromium extension context
- screenshots: browser capture

위 도구들은 예시이며 Project OS dependency가 아닙니다.

## 13. Schema Validation

현재 schema:

```text
schemas/qa-manifest.schema.json
schemas/qa-scenario.schema.json
schemas/qa-result.schema.json
```

YAML Manifest/Scenario도 YAML을 object로 파싱한 뒤 JSON Schema로 validation할 수 있습니다.

CI에서는 다음을 검증합니다.

- Manifest schema
- Scenario schema
- Result schema
- PASS
- PASS_WITH_WARNINGS
- FAIL
- HUMAN_GATE_REQUIRED
- repository-relative Artifact path
- Screenshot metadata
- Visual Review category
- scaffold install regression
- Linux runner smoke
- Windows PowerShell runner smoke
- 기존 Project OS regression suite

## 14. Versioning / Legacy v1

QA Contract version은 Project OS consumer canonical schema와 분리합니다.

현재:

- Project OS package: 0.4.0
- base scaffold: 0.4.0
- consumer canonical schema: 1
- QA Contract: 2.0
- legacy QA Result: 1.0
- central DB schema: 1

Legacy result schema:

```text
schemas/qa-result-v1.schema.json
```

기존 v1 consumer는 자동으로 덮어쓰지 않습니다. v1의 특징은 다음과 같습니다.

```text
scripts/qa.ps1
.qa/runs/<run-id>/result.json
schema_version: "1.0"
PASS | FAIL | UI_REVIEW_REQUIRED
```

Remote Control이 legacy 지원을 유지하려면:

1. `.qa/manifest.yaml`이 있으면 v2로 처리합니다.
2. manifest가 없고 `scripts/qa.ps1`이 존재하면 legacy v1 adapter를 사용할 수 있습니다.
3. v1 result는 `schemas/qa-result-v1.schema.json`으로 검증합니다.

기존 v1 project에서 `projectctl qa-init`을 강제로 실행해 덮어쓰지 마세요. manifest/runner/scenario를 프로젝트별 구현과 함께 명시적으로 migration하는 방식을 사용합니다.

## 15. 완료 조건

QA-enabled consumer project는 다음 조건을 만족해야 합니다.

- Manifest가 현재 schema와 일치
- Scenario가 사용하는 경우 schema와 일치
- runner가 host command를 제공
- runner가 가능한 실패 상황에서도 result를 생성
- result가 현재 schema와 일치
- artifact path가 repository-relative
- screenshot metadata가 priority/kind를 제공
- visual review가 구조화된 issue를 제공
- Remote Control이 프로젝트 기술을 몰라도 manifest/result만으로 결과를 읽을 수 있음
