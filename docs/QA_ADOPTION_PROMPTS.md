# Existing Project QA Adoption Prompts

이 문서는 이미 개발 중인 프로젝트에 **Project OS Automated QA Contract v2**를 적용할 때 사용하는 실전 가이드와 복사 가능한 Agent Prompt를 제공합니다.

Project OS가 정의하는 것은 공통 Contract뿐입니다.

```text
.qa/manifest.yaml
    ↓
project-specific QA runner
    ↓
.qa/runs/<run-id>/result.json
    ↓
artifacts[] + visualReviews[]
```

실제 테스트 기술은 각 프로젝트가 현재 사용 중인 기술과 기존 테스트 자산을 우선 사용합니다.

---

## 1. 적용 전 공통 원칙

작업 전에 반드시 현재 repository를 먼저 확인합니다.

```text
README.md
AGENTS.md
PROJECT.md
.project-os/manifest.yaml
.project-os/state/current.yaml
.project-os/state/backlog.yaml
기존 CI
기존 test / smoke / QA script
기존 screenshot / visual QA 도구
```

그 다음 QA 상태를 다음 세 가지 중 하나로 분류합니다.

### A. QA가 없는 프로젝트

`.qa/manifest.yaml`도 없고 legacy `scripts/qa.ps1`도 없다면:

```powershell
projectctl qa-init
```

이후 생성된 scaffold를 프로젝트에 맞게 구현합니다.

### B. QA Contract v2가 이미 있는 프로젝트

`.qa/manifest.yaml`이 있다면 다시 `qa-init`하지 않습니다.

현재 Manifest / Runner / Scenario를 읽고 부족한 stage와 scenario만 확장합니다.

### C. Legacy QA v1이 있는 프로젝트

아래 형태가 있으면 v1일 가능성이 높습니다.

```text
scripts/qa.ps1
qa/
.qa/runs/
schema_version: "1.0"
UI_REVIEW_REQUIRED
```

이 경우:

- `projectctl qa-init --force`를 사용하지 않습니다.
- 기존 runner 로직을 먼저 읽습니다.
- 실제 build/test/screenshot 로직을 최대한 재사용합니다.
- 새 `.qa/manifest.yaml`과 `.qa/scripts/run-qa.*` 구조로 이동합니다.
- Result를 QA Contract v2로 변환합니다.
- v2 QA가 성공한 뒤에만 legacy entry point 정리를 검토합니다.

## 2. 모든 프로젝트에서 지켜야 할 구현 규칙

- Project OS Contract를 프로젝트 기술에 맞추지 말고, 프로젝트 Runner를 Contract에 맞춥니다.
- Playwright, Godot, Android, Chromium 등의 dependency를 Project OS에 추가하지 않습니다.
- Telegram / Remote Control / Host orchestration 코드는 consumer project QA에 추가하지 않습니다.
- 가능한 실패 상황에서도 `result.json`을 남깁니다.
- 실행되지 않은 검증을 `PASS`로 기록하지 않습니다.
- Artifact path는 repository root 기준 상대경로 + forward slash를 사용합니다.
- Screenshot은 가능하면 `scenarioId`, `step`, `caption`, `kind`, `priority`를 기록합니다.
- 사람이 판단해야 하는 사항은 억지로 자동 PASS 처리하지 않고 `HUMAN_GATE_REQUIRED`로 남깁니다.
- QA 도입을 위해 제품 기능이나 디자인을 불필요하게 변경하지 않습니다.
- 테스트를 위한 hook이 꼭 필요하면 최소 범위로 만들고 이유를 문서화합니다.

---

# 3. DeskTown

DeskTown은 Windows Desktop + Godot 4.x + C# 프로젝트이므로, 기존 Windows QA 자산을 최대한 재사용하는 것이 우선입니다.

특히 repository에 기존 `desktown-windows-qa-kit`, `preflight.ps1`, smoke test, process launch script가 있다면 새로 중복 구현하지 않습니다.

## 적용 Prompt

```text
Repository:
https://github.com/Seunghyun0606/desktown

목적:
현재 DeskTown repository에 Project OS Automated QA Contract v2를 적용해라.

중요:
이번 작업은 QA Contract adapter를 만드는 작업이다.
게임 기능이나 UX 방향을 임의로 변경하지 마라.
Telegram, Remote Control, Host orchestration, Codex/Claude orchestration을 이 repository에 구현하지 마라.

작업 시작 전에 최신 remote를 fetch하고 현재 repository 상태를 확인해라.

반드시 먼저 읽고 확인:
1. README.md
2. AGENTS.md
3. PROJECT.md
4. .project-os/manifest.yaml
5. .project-os/state/current.yaml
6. .project-os/state/backlog.yaml
7. Godot project 설정
8. C# solution/project 설정
9. 기존 test / smoke / QA script
10. desktown-windows-qa-kit가 있다면 전체 구조
11. preflight.ps1 또는 Windows smoke script
12. CI workflow

Project OS QA Contract 기준:
- Contract version: 2.0
- discovery: .qa/manifest.yaml
- Windows runner: .qa/scripts/run-qa.ps1
- output: .qa/runs/<runId>/result.json
- run status:
  PASS
  PASS_WITH_WARNINGS
  FAIL
  HUMAN_GATE_REQUIRED
- artifact path는 repository-relative forward-slash path

먼저 현재 QA 상태를 판별해라.

A. .qa/manifest.yaml이 이미 있으면 기존 v2를 확장한다.
B. QA가 전혀 없으면 projectctl qa-init을 사용한다.
C. legacy scripts/qa.ps1 또는 schema_version 1.0 QA가 있으면
   projectctl qa-init --force를 사용하지 말고 기존 QA 로직을 v2 구조로 migration한다.

DeskTown에서는 새 QA 구현보다 기존 Windows QA kit와 smoke/preflight 로직 재사용을 최우선으로 한다.

권장 stage:
- preflight
- build
- unit
- integration
- smoke
- ui
- visual
- cleanup

단 실제 repository에서 지원하지 않는 stage는 억지로 구현하지 말고 manifest에서 제외하거나 SKIPPED 처리한다.

최소 자동 QA scenario는 현재 구현된 기능을 기준으로 구성한다.

후보:
1. app_startup
   - executable/game launch
   - main window 표시
   - startup crash 없음
   - initial screenshot

2. focus_session
   - Focus 시작 가능
   - session running 상태 확인
   - timer/state 변화 확인
   - 중요한 screenshot 저장

3. companion_stage
   - Mina CompanionStage가 현재 구현되어 있다면 표시 확인
   - Work/Rest/Stretch/Walk 상태 mapping이 존재하면 최소 상태 전환 검증
   - screenshot 저장

4. hidden_mode
   - 구현되어 있다면 Hidden lifecycle 진입/복귀
   - Hidden 상태에서도 reward/session logic이 깨지지 않는지 기존 테스트 범위에서 검증

5. ghost_overlay
   - 구현되어 있다면 overlay launch
   - transparent/always-on-top/non-interactive 요구를 자동으로 확인 가능한 범위까지 검증
   - 시각적 최종 판단이 필요하면 HUMAN_GATE_REQUIRED로 남긴다.

6. main_town
   - 현재 구현되어 있을 때만 startup/navigation smoke와 screenshot을 추가한다.

중요:
아직 구현되지 않은 feature를 QA를 위해 새로 만들지 마라.
현재 repository 상태에 존재하는 기능만 scenario로 등록해라.

Screenshot:
- main launch: initial / normal
- focus running: result / important
- companion stage: checkpoint 또는 result / important
- failure screenshot: failure / failure
- visual diff가 있으면 visual_diff / important

Visual Review에서 필요한 경우:
- clipping
- overlap
- alignment
- readability
- missing_asset
- unexpected_layout
- visual_regression
- hierarchy
- obstruction

runner는 가능한 실패 상황에서도 result.json을 생성해야 한다.

기존 QA kit의 isolated write, PowerShell execution policy, temporary directory 처리 등
이미 해결된 로직이 있다면 새 runner에서도 재사용해라.

작업 완료 전:
1. manifest 구조 검증
2. runner manual smoke
3. result.json 2.0 형식 확인
4. artifact relative path 확인
5. Windows PowerShell 환경에서 QA 실행
6. 기존 test/CI regression 확인
7. projectctl doctor 실행

마지막 보고:
- 기존 QA 구조 분석
- v1 여부
- 생성/변경한 .qa 파일
- 재사용한 기존 QA kit/script
- 실제 지원 stage
- 실제 등록 scenario
- QA 실행 결과
- result.json 경로
- 생성 artifact
- HUMAN_GATE_REQUIRED 항목
- 남은 TODO
```

---

# 4. Nothing Wrong

Nothing Wrong은 Web 우선 프로젝트이므로 기존 package manager, test runner, browser/e2e 환경을 먼저 확인합니다.

Playwright는 적합한 후보이지만 **이미 다른 도구가 있다면 교체하지 않습니다.**

## 적용 Prompt

```text
목적:
현재 Nothing Wrong repository에 Project OS Automated QA Contract v2를 적용해라.

이번 작업은 프로젝트별 Web QA adapter를 만드는 작업이다.
게임 스토리, 밸런스, UI 디자인 방향을 임의로 변경하지 마라.
Telegram / Remote Control 코드는 구현하지 마라.

작업 시작 전에 최신 remote를 fetch하고 다음을 확인해라.

1. README.md
2. AGENTS.md
3. PROJECT.md
4. .project-os/manifest.yaml
5. .project-os/state/current.yaml
6. package.json 및 lock file
7. build/dev/start script
8. 기존 unit/integration/e2e test
9. Playwright/Cypress/Vitest/Jest 등 기존 설정
10. CI workflow
11. screenshot 또는 visual regression 관련 코드

QA 상태 판별:
- .qa/manifest.yaml이 있으면 기존 v2 확장
- QA가 없으면 projectctl qa-init
- legacy scripts/qa.ps1/schema_version 1.0이 있으면 force overwrite 금지 후 v2 migration

Project OS QA Contract:
- schemaVersion: 2.0
- .qa/manifest.yaml
- Windows/Unix command는 현재 프로젝트 실행 환경에 맞게 정의
- .qa/runs/<runId>/result.json
- repository-relative artifact paths

기존 Web test stack을 최우선으로 재사용해라.
현재 e2e 도구가 없다면 repository 구조를 보고 가장 작은 변경으로 브라우저 smoke/UI 검증을 추가하되,
Project OS 자체에는 dependency를 추가하지 마라.

권장 stage:
- build
- unit
- integration
- smoke
- ui
- visual

최소 scenario는 실제 구현 상태를 기준으로 아래에서 선택한다.

1. app_boot
   - app/server startup
   - 첫 화면 load
   - console/runtime fatal error 없음
   - initial screenshot

2. inbox_ticket_flow
   - Inbox가 구현되어 있다면 Ticket 진입
   - 요구사항/업무 화면 표시
   - 주요 UI screenshot

3. fake_service_flow
   - 테스트 대상 Fake Service가 구현되어 있다면 진입
   - 핵심 interaction smoke
   - runtime error 없음

4. bug_report_flow
   - Bug Report 작성 기능이 구현되어 있다면 최소 입력/submit
   - 결과 상태 확인

5. qa_review_flow
   - QA Lead Review/결과 화면이 구현되어 있을 때만 상태 전환 확인

6. visual_baseline
   - 핵심 화면 screenshot
   - visual reviewer가 있다면 visualReviews[] 생성

실제 로그인/회사 계정/외부 API가 필요하지 않도록
현재 프로젝트의 local fixture/mock/demo flow를 우선 사용해라.
외부 실제 서비스나 사용자 계정에 의존하는 테스트를 새로 만들지 마라.

Screenshot priority:
- app initial: normal
- Ticket/Fake Service 핵심 화면: important
- Bug report 결과: important
- 실패 상태: failure

Visual Review:
- fake browser UI와 game UI가 구분되는지 자동 판별 가능한 범위
- clipping
- overlap
- alignment
- readability
- unexpected_layout
- hierarchy
- obstruction

아직 구현되지 않은 스토리/화면을 QA를 위해 만들지 마라.

완료 전:
- build/test 실행
- QA runner 실행
- result.json v2 확인
- screenshot metadata 확인
- artifact path 확인
- 기존 CI regression 확인
- projectctl doctor

마지막 보고:
- 사용한 기존 Web test stack
- QA manifest
- stage
- scenario
- 실행 결과
- screenshots/visual review
- 실패 또는 warning
- Human Gate
- 남은 TODO
```

---

# 5. The Orpheus Project

The Orpheus Project는 현재 repository의 실제 runtime/engine 구성을 먼저 확인해야 합니다.

엔진이나 framework를 추측해서 강제하지 않습니다.

## 적용 Prompt

```text
목적:
현재 The Orpheus Project repository에 Project OS Automated QA Contract v2를 적용해라.

이번 작업에서는 narrative/game content를 변경하지 말고 QA adapter와 자동 검증 구조만 추가해라.
Telegram / Remote Control / provider orchestration은 구현하지 마라.

작업 전에 최신 remote fetch 후 다음을 확인해라.

1. README.md
2. AGENTS.md
3. PROJECT.md
4. .project-os/manifest.yaml
5. .project-os/state/current.yaml
6. 실제 runtime/engine/framework
7. build/run command
8. 기존 automated test
9. 기존 smoke/e2e/visual test
10. CI workflow
11. 현재 구현된 화면/flow

QA 상태 판별:
- v2 manifest가 있으면 확장
- QA가 없으면 projectctl qa-init
- legacy QA가 있으면 --force 금지 후 migration

QA Contract:
- schemaVersion 2.0
- .qa/manifest.yaml
- .qa/scripts/run-qa.ps1 또는 run-qa.sh
- .qa/runs/<runId>/result.json
- repository-relative artifacts

실제 framework를 확인한 뒤 project-specific runner를 구현한다.
Project OS에 특정 engine dependency를 추가하지 않는다.

현재 구현된 범위 안에서 최소 scenario를 정의한다.

후보:
1. app_startup
   - app 실행
   - main/terminal 화면 표시
   - startup fatal error 없음

2. incident_entry
   - Pager/Incident entry가 구현되어 있으면 진입
   - incident 정보 표시
   - screenshot

3. investigation_view
   - Logs/Metrics 조사 화면이 구현되어 있으면 표시/interaction smoke
   - screenshot

4. action_flow
   - 현재 구현된 Action 선택/실행 흐름
   - 상태 변화 확인

5. incident_resolution
   - 현재 구현되어 있다면 incident 완료/root cause/postmortem 진입 smoke

6. visual_terminal
   - CRT/terminal UI 주요 화면 screenshot
   - readability/hierarchy/obstruction visual review

현재 구현되지 않은 chapter, ending, narrative branch는 QA를 위해 생성하지 마라.

Visual Review category:
- readability
- clipping
- alignment
- hierarchy
- obstruction
- unexpected_layout
- visual_regression

CRT 효과나 시각 스타일의 최종 미감 판단처럼 자동 판별하기 어려운 항목은
필요하면 HUMAN_GATE_REQUIRED로 남긴다.

완료 전:
- 기존 테스트 regression
- QA runner manual run
- valid result.json v2
- artifact relative path
- screenshot metadata
- projectctl doctor

마지막 보고:
- 확인한 runtime/engine
- 재사용한 기존 test
- manifest/stage
- scenarios
- QA 결과
- screenshot/visual review
- Human Gate
- 남은 TODO
```

---

# 6. Tab Pets

Tab Pets는 Chrome Extension이므로 일반 Web app과 달리 **실제 개인 Chrome profile을 사용하지 않는 격리된 extension test context**가 중요합니다.

## 적용 Prompt

```text
목적:
현재 Tab Pets repository에 Project OS Automated QA Contract v2를 적용해라.

이번 작업은 Chrome Extension용 QA adapter 구현이다.
제품 UX나 Pet 동작 정책을 임의로 변경하지 마라.
Telegram / Remote Control은 구현하지 마라.

최신 remote fetch 후 먼저 확인:
1. README.md
2. AGENTS.md
3. PROJECT.md
4. .project-os/manifest.yaml
5. .project-os/state/current.yaml
6. package.json / lock file
7. Chrome Extension manifest
8. build/bundle script
9. content script / background/service worker 구조
10. popup/status room/settings UI
11. 기존 browser/e2e test
12. CI workflow

QA 상태:
- v2 manifest 존재 → 확장
- QA 없음 → projectctl qa-init
- legacy QA 존재 → force 금지 후 v2 migration

Contract:
- schemaVersion 2.0
- .qa/manifest.yaml
- runner output .qa/runs/<runId>/result.json
- repository-relative artifacts

Chrome Extension QA는 사용자 실제 Chrome profile을 사용하지 마라.
가능하면 temporary/isolated browser profile 또는 test context를 사용한다.
현재 browser automation 도구가 있으면 재사용한다.
Playwright/Chromium이 적합하더라도 기존 stack을 무조건 교체하지 마라.

권장 stage:
- build
- unit
- integration
- smoke
- ui
- visual

현재 구현된 기능만 기준으로 scenario를 선택한다.

후보:
1. extension_load
   - extension build/load
   - manifest/runtime error 없음

2. pet_injection
   - content script가 구현되어 있다면 test page에 Pet 표시
   - screenshot
   - 페이지 interaction을 불필요하게 막지 않는지 기본 smoke

3. pet_state
   - 현재 구현된 animation/status 변화 중 자동 검증 가능한 상태 확인

4. room_or_status_ui
   - popup/status room이 구현되어 있다면 open
   - main state 표시
   - screenshot

5. bring_home
   - '집으로 불러들이기' 또는 pet hide 기능이 실제 구현되어 있을 때만
   - 상태 변경 및 persistence 확인

6. persistence
   - reload/reopen 후 저장 대상 상태가 유지되는지 현재 요구사항 범위에서 확인

7. visual_extension
   - Pet overlay와 room/status UI의 clipping/obstruction/readability 확인

아직 구현되지 않은 Pet 종류, 관리 빈도, animation을 QA 때문에 추가하지 마라.

특히:
- 실제 사용자의 탭/쿠키/로그인 정보를 테스트에서 읽지 마라.
- 외부 사이트에 destructive interaction을 하지 마라.
- local fixture/test page를 우선 사용한다.

Screenshot:
- pet visible: important
- room/status UI: important
- failure: failure

완료 전:
- extension build
- isolated load smoke
- QA runner
- result.json v2
- artifact/screenshot metadata
- existing tests
- projectctl doctor

마지막 보고:
- extension architecture
- browser test 방식
- manifest/stage
- scenario
- QA 결과
- screenshot
- Human Gate
- 남은 TODO
```

---

# 7. DailyTown

DailyTown은 Android 프로젝트이며 기존 Emulator Replay / Visual QA 자산이 이미 존재할 수 있으므로 이를 새로 복제하지 않고 adapter로 감싸는 것이 핵심입니다.

## 적용 Prompt

```text
Repository:
https://github.com/Seunghyun0606/dailytown

목적:
현재 DailyTown repository에 Project OS Automated QA Contract v2를 적용해라.

이번 작업은 기존 Android/Emulator QA를 Project OS 공통 Contract에 연결하는 작업이다.
Moru canonical asset, 디자인 baseline, 제품 기능을 QA 적용을 이유로 임의 수정하지 마라.
Telegram / Remote Control / Android host orchestration을 이 repository에 구현하지 마라.

작업 시작 시 최신 remote fetch 후 현재 active development branch와 HEAD를 확인해라.
과거 branch/head 정보를 고정값으로 가정하지 마라.

반드시 확인:
1. README.md
2. AGENTS.md
3. PROJECT.md
4. .project-os/manifest.yaml
5. .project-os/state/current.yaml
6. Android Gradle 구조
7. 기존 Android CI
8. emulator test harness
9. Emulator Replay / Visual QA script
10. screenshot/replay artifact 생성 구조
11. instrumentation/UI test 설정
12. companion/Moru runtime profile 설정

QA 상태 판별:
- .qa/manifest.yaml 존재 → 기존 v2 확장
- QA 없음 → projectctl qa-init
- scripts/qa.ps1/schema_version 1.0 legacy가 있으면 force overwrite 금지 후 migration

Project OS QA Contract:
- schemaVersion 2.0
- .qa/manifest.yaml
- Windows/Unix command는 현재 개발/CI 환경에 맞게 정의
- result: .qa/runs/<runId>/result.json
- repository-relative artifacts

기존 Android CI / emulator replay / visual QA가 있다면
그 로직을 다시 만들지 말고 .qa runner가 호출하고 결과를 v2 result로 normalize하는 adapter 형태를 우선 사용한다.

권장 stage:
- preflight
- build
- unit
- integration
- smoke
- ui
- visual
- cleanup

실제 repository 상태에 맞춰 최소 scenario를 정의한다.

후보:
1. app_launch
   - Android build/install
   - target Activity launch
   - startup crash 없음
   - screenshot

2. companion_visible
   - 현재 canonical companion profile이 구현되어 있다면 Moru 표시 확인
   - runtime profile이 repository에서 여전히 companion.moru.canonical.v2라면 이를 재사용
   - profile 이름이 변경되었으면 현재 값을 사용
   - screenshot important

3. core_exploration_smoke
   - 현재 구현된 walk/discovery/clue flow 중 existing emulator harness가 이미 검증하는 범위만 등록

4. replay_regression
   - 기존 Emulator Replay가 있다면 결과를 integration/ui stage에 연결

5. visual_regression
   - 기존 Visual QA가 있다면 screenshot/visual diff artifact를 Contract 형식으로 normalize

6. physical_readability
   - outdoor readability처럼 실제 기기/사람 판단이 필요한 gate가 현재도 존재하면 자동 PASS 처리하지 마라.
   - scenario/result에서 HUMAN_GATE_REQUIRED로 표현하고 관련 screenshot/metadata를 남긴다.

중요:
- canonical Moru raster/semantic asset을 QA 작업에서 수정하지 마라.
- Android Emulator lifecycle 관리가 이미 별도 tooling/Remote Control 책임이면 Project OS contract layer로 끌어오지 마라.
- 기존 CI나 emulator harness가 제공하는 artifact를 최대한 재사용해라.

Screenshot:
- initial app: initial / normal
- Moru visible: result / important
- failure: failure / failure
- visual diff: visual_diff / important

완료 전:
- Gradle/build test
- existing emulator/replay test
- QA runner
- result.json v2
- artifact path
- screenshot metadata
- existing CI regression
- projectctl doctor

마지막 보고:
- active branch/head
- 기존 Android QA 자산
- 재사용한 harness/script
- manifest/stages
- scenarios
- 자동 QA 결과
- screenshot/visual diff
- HUMAN_GATE_REQUIRED
- 남은 TODO
```

---

# 8. 다른 프로젝트용 공통 Prompt Template

새 프로젝트에도 같은 방식으로 적용할 수 있습니다.

```text
현재 repository에 Project OS Automated QA Contract v2를 적용해라.

먼저 repository의 실제 기술 구조와 기존 QA/test 자산을 분석해라.
새 테스트 framework를 바로 추가하지 말고 기존 build/test/smoke/e2e/visual 도구를 최우선으로 재사용해라.

반드시 확인:
- README.md
- AGENTS.md
- PROJECT.md
- .project-os/manifest.yaml
- .project-os/state/current.yaml
- build/run scripts
- existing tests
- CI
- QA/smoke/screenshot scripts

QA 상태 판별:
1. .qa/manifest.yaml 있음 → 기존 v2 확장
2. QA 없음 → projectctl qa-init
3. legacy scripts/qa.ps1 또는 schema_version 1.0 → --force 금지 후 v2 migration

Contract:
- schemaVersion 2.0
- .qa/manifest.yaml
- .qa/scripts/run-qa.*
- .qa/runs/<runId>/result.json
- PASS / PASS_WITH_WARNINGS / FAIL / HUMAN_GATE_REQUIRED
- artifact paths are repository-relative
- screenshots include caption/kind/priority where applicable

현재 구현된 기능만 scenario로 정의한다.
QA를 위해 미구현 제품 기능을 만들지 마라.

실행되지 않은 검증은 PASS로 기록하지 않는다.
실패해도 가능한 경우 result.json을 남긴다.
사람 판단이 필요한 경우 HUMAN_GATE_REQUIRED를 사용한다.

Telegram / Remote Control / host/provider orchestration은 구현하지 마라.

완료 전:
- existing regression tests
- QA runner smoke
- result schema 확인
- artifact path 확인
- projectctl doctor

마지막 보고:
- 기존 구조
- QA 상태(v1/v2/none)
- 변경 파일
- stages
- scenarios
- QA 결과
- artifacts
- Human Gate
- TODO
```
