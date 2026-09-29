# Project OS Setup Prompts

이 문서는 어떤 프로젝트에도 재사용할 수 있는 **Project OS + Automated QA 표준 도입 Prompt**를 제공합니다.

두 경우만 구분하면 됩니다.

| 상황 | 사용할 Prompt |
| --- | --- |
| 프로젝트를 이제 시작하거나 scaffold를 처음 만드는 단계 | 초기 세팅 Prompt |
| 이미 코드/문서/테스트가 존재하고 개발이 진행 중인 단계 | 프로젝트 중간 도입 Prompt |

두 Prompt 모두 특정 기술 스택을 가정하지 않습니다. Web, Android, Windows Desktop, Game, Chrome Extension, CLI 등 실제 repository를 먼저 분석한 뒤 현재 도구를 최대한 재사용하도록 설계되어 있습니다.

---

## 1. 공통 원칙

두 경우 모두 아래 원칙을 지킵니다.

- 최신 remote와 현재 branch/HEAD를 먼저 확인합니다.
- 기존 파일을 `--force`로 덮어쓰지 않습니다.
- Project OS는 canonical project state와 Contract를 담당합니다.
- 실제 build/test/UI automation은 각 프로젝트가 담당합니다.
- 이미 존재하는 build/test/smoke/e2e/visual QA를 우선 재사용합니다.
- Telegram, Remote Control, Host 관리, Codex/Claude orchestration은 consumer repository에 구현하지 않습니다.
- 구현되지 않은 제품 기능을 Project OS/QA 도입을 위해 새로 만들지 않습니다.
- Project OS consumer schema와 QA Contract version은 별개로 취급합니다.
- 작업 마지막에는 `projectctl doctor`와 가능한 regression test를 실행합니다.

---

# 2. 프로젝트 초기 세팅 Prompt

다음 Prompt는 **새 프로젝트를 만들었거나 아직 개발이 본격적으로 시작되지 않은 repository**에 사용합니다.

필요한 경우 아래 placeholder만 바꿉니다.

- `[REPOSITORY_URL]`
- `[PROJECT_NAME]`
- `[INITIAL_PLAN]` 또는 기획 문서 경로

## 복사용 Prompt

```text
Repository:
[REPOSITORY_URL]

Project:
[PROJECT_NAME]

목적:
이 repository를 Project OS 기반으로 초기 세팅하고,
가능한 경우 Automated QA Contract v2까지 함께 구성해라.

이번 단계의 목적은 제품 기능을 많이 구현하는 것이 아니라,
앞으로 여러 Agent/Codex 세션이 같은 canonical state를 읽고
안전하게 이어서 작업할 수 있는 프로젝트 운영 기반을 만드는 것이다.

Project OS repository:
https://github.com/Seunghyun0606/project-os

현재 Project OS 기준:
- package/scaffold: 현재 설치된 최신 호환 버전을 확인해서 사용
- consumer canonical schema: .project-os/manifest.yaml 기준
- Automated QA Contract: schemaVersion 2.0
- QA discovery: .qa/manifest.yaml

작업 시작 전에 최신 remote를 fetch하고 현재 branch/HEAD를 확인해라.

먼저 repository를 조사해라.

필수 확인:
1. README.md
2. AGENTS.md가 이미 있는지
3. PROJECT.md가 이미 있는지
4. 기존 docs/, specs/, 기획 문서
5. source directory
6. package/build/runtime 설정
7. test / lint / CI 설정
8. 기존 QA / smoke / screenshot / visual test
9. Git history가 이미 있다면 최근 주요 commit
10. Project OS가 이미 설치되어 있는지
11. .qa/manifest.yaml 또는 legacy QA가 있는지

중요:
Project OS가 이미 설치되어 있다면 다시 init하지 말고 현재 구조를 확장해라.
기존 프로젝트 파일이 있으면 --force로 덮어쓰지 마라.

────────────────
A. Project OS 초기화
────────────────

Project OS가 아직 없다면 프로젝트 루트에 base scaffold를 설치해라.

QA도 처음부터 사용하는 것이 적절한 프로젝트라면:

projectctl init --with-qa

자동 UI/runtime QA가 아직 의미 없는 library/package 등이라면
base scaffold만 설치하고 QA는 실제 실행 대상이 생길 때 추가해도 된다.

projectctl init

기존 README, docs, source code를 Project OS 형식에 맞추기 위해 불필요하게 이동하지 마라.

────────────────
B. 최초 기획 구조화
────────────────

아래 기획 정보를 Source of Truth 후보로 사용해라.

[INITIAL_PLAN]

기획 문서가 repository 안에 별도 파일로 있다면 원문을 보존하고,
가능하면 specs/product/ 아래 또는 기존 문서 위치를 reference로 사용해라.

PROJECT.md에는 장기간 유지해야 할 핵심만 정리한다.

최소:
- Vision
- Target User
- Core Experience
- Product Principles
- Architecture/Platform Constraints
- Non-goals
- Success Definition

세부 요구사항 전체를 PROJECT.md에 복사하지 마라.

상세 내용은 필요에 따라:
- specs/product/
- specs/feature/
- specs/architecture/
- specs/ux/

로 분리한다.

────────────────
C. Roadmap / Backlog / Task
────────────────

프로젝트를 구현 가능한 Milestone으로 나눠라.

.project-os/state/roadmap.yaml:
- 큰 개발 단계
- milestone 목적
- 완료 조건

.project-os/state/backlog.yaml:
- 첫 Milestone에서 실제 실행할 Task
- priority
- dependency
- status

현재 바로 실행할 수 있는 Task만
.project-os/tasks/ 아래 canonical Task contract로 구체화한다.

Task에는 최소:
- goal
- rationale
- include scope
- exclude scope
- references
- acceptance criteria
- verification
- dependencies

를 포함한다.

초기 단계에서 불필요하게 수십 개 Task를 미리 상세화하지 마라.

────────────────
D. Decision / Quality Gate
────────────────

이미 확정된 중요한 선택만
.project-os/decisions/에 기록한다.

예:
- target platform
- framework/engine
- data/storage 원칙
- 호환성 정책
- 운영상 변경 금지 제약

.project-os/quality/gates.yaml은
현재 프로젝트 기술에 맞춰 최소 quality gate를 설정한다.

가능한 예:
- build
- lint
- unit
- integration
- smoke
- QA

존재하지 않는 검증을 억지로 필수화하지 마라.

────────────────
E. Automated QA Contract v2
────────────────

QA가 필요한 프로젝트라면 .qa/를 구성한다.

기준:
- .qa/manifest.yaml
- .qa/scripts/run-qa.ps1 또는 run-qa.sh
- .qa/scenarios/
- .qa/runs/<runId>/result.json
- repository-relative artifacts

Project OS가 특정 test framework를 강제하지 않는다.

현재 repository에서 이미 사용하는 test/build 도구가 있으면 재사용한다.

manifest에는 실제 지원 가능한 stage만 등록한다.

후보:
- preflight
- build
- unit
- integration
- smoke
- ui
- visual
- cleanup

초기 QA scenario는 현재 실제로 실행 가능한 최소 흐름만 정의한다.

예:
- application/package startup
- 기본 smoke
- 핵심 첫 화면
- 가장 중요한 primary flow 1개

아직 구현되지 않은 기능을 QA scenario 때문에 구현하지 마라.

Screenshot이 의미 있는 프로젝트라면:
- initial
- checkpoint
- result
- failure
- visual_diff

와 priority:
- normal
- important
- failure

를 사용한다.

사람의 판단이 필요한 검증은
억지로 PASS 처리하지 말고 HUMAN_GATE_REQUIRED로 남길 수 있게 설계한다.

기본 scaffold runner가 QA_NOT_CONFIGURED를 반환하는 경우,
실제 프로젝트 QA가 준비되기 전에는 이를 거짓 PASS로 바꾸지 마라.

────────────────
F. 검증
────────────────

최종적으로 가능한 범위에서 다음을 실행해라.

1. projectctl version
2. projectctl doctor
3. projectctl status
4. projectctl next --role developer
5. 기존 build/test/lint
6. QA를 구현했다면 QA runner manual smoke
7. result.json schemaVersion 2.0 확인
8. artifact relative path 확인

제품 방향을 바꾸는 수준의 불확실성만 Human Gate로 남겨라.
단순한 파일명/구현 세부 선택 때문에 작업을 멈추지 마라.

이번 세팅 단계에서 실제 제품 기능 개발을 과도하게 진행하지 마라.

마지막에 다음 형식으로 보고해라.

1. Project OS 설치/기존 여부
2. 생성/수정한 구조
3. PROJECT.md 핵심
4. Milestone
5. Backlog / 첫 Task
6. Decision
7. Quality Gate
8. QA 적용 여부
9. QA stages/scenarios
10. 실행한 검증과 결과
11. Human Gate
12. 다음 실행 가능한 Task
```

---

# 3. 프로젝트 중간 도입 Prompt

다음 Prompt는 **이미 개발이 진행 중이고 코드, 문서, TODO, 테스트, Git history가 쌓인 repository**에 사용합니다.

핵심은 과거를 전부 Project OS Task로 재작성하는 것이 아닙니다.

```text
과거 → 중요한 Milestone/Decision만 요약
현재 → 실제 코드/문서/테스트 상태를 정확히 복원
미래 → Project OS Task/QA Contract로 상세 관리
```

## 복사용 Prompt

```text
Repository:
[REPOSITORY_URL]

Project:
[PROJECT_NAME]

목적:
이미 개발이 진행 중인 이 repository에
Project OS와 Automated QA Contract v2를 안전하게 중간 도입해라.

이번 작업의 목적은 새 제품 기능 구현이 아니다.

현재 repository의 실제 상태를 분석하고,
기존 코드/문서/테스트/QA 자산을 최대한 보존하면서
앞으로의 작업을 Project OS canonical state와 QA Contract로 관리할 수 있게 만드는 것이다.

Project OS repository:
https://github.com/Seunghyun0606/project-os

중요 원칙:
- 기존 파일을 --force로 덮어쓰지 마라.
- 과거 완료 작업을 세부 Task로 전부 역생성하지 마라.
- 현재 구현을 추측하지 말고 코드와 실제 test/runtime evidence를 확인해라.
- 기존 QA/test framework를 우선 재사용해라.
- QA 도입을 위해 제품 기능을 새로 만들지 마라.
- Telegram / Remote Control / Host / provider orchestration을 이 repository에 구현하지 마라.

작업 시작 전에 최신 remote를 fetch하고 현재 branch/HEAD를 확인해라.

가능하면 별도 adoption branch에서 작업해라.

────────────────
A. Repository Inventory
────────────────

먼저 아무 기능도 수정하지 말고 현재 상태를 조사해라.

반드시 확인:
1. README.md
2. AGENTS.md
3. PROJECT.md
4. 기존 docs/, specs/, design/architecture 문서
5. 주요 source directory
6. package/build/runtime 설정
7. 현재 branch와 최근 Git history
8. TODO / issue / backlog / task 관련 파일
9. test / lint / CI
10. smoke/e2e/UI/visual QA
11. 실행/배포 script
12. .project-os/ 존재 여부와 현재 state
13. .qa/manifest.yaml 존재 여부
14. legacy scripts/qa.ps1 / schema_version 1.0 존재 여부

Repository Inventory 결과로 다음을 분리해라.

- 완료된 기능
- 현재 진행 중 기능
- 실제 미완료 기능
- 문서상 TODO지만 이미 구현된 항목
- 코드에는 있지만 문서에 없는 기능
- 앞으로도 유효한 architecture decision
- test/CI/QA coverage
- 현재 blocker

────────────────
B. Project OS 상태 판별
────────────────

1. .project-os가 없으면:
   projectctl init을 검토한다.

단 기존 PROJECT.md/AGENTS.md 등과 충돌하면
--force를 사용하지 말고 scaffold와 기존 파일을 비교해 수동 병합한다.

2. .project-os가 이미 있으면:
   다시 init하지 마라.
   기존 canonical state를 읽고 불일치만 수정한다.

기존 프로젝트의 문서를 Project OS 도입 때문에 전부 이동하지 마라.

────────────────
C. Canonical State 복원
────────────────

PROJECT.md:
앞으로도 유지할 장기 방향만 복원한다.

최소:
- Vision
- Target User
- Core Experience
- Product Principles
- Architecture Constraints
- Non-goals
- Success Definition

Roadmap:
이미 완료된 주요 단계는 Milestone 수준으로만 요약한다.

예:
- M1 Foundation: completed
- M2 Core MVP: completed
- M3 Integration: active
- M4 Production QA: planned

과거 완료 작업의 세부 Task를 전부 만들지 마라.

Backlog:
기존 TODO를 그대로 복사하지 말고
코드/문서/test 상태와 대조해서 앞으로 실제 해야 할 일만 등록한다.

Task:
현재 진행 중이거나 다음 실행 가능한 작업부터 상세 canonical Task를 만든다.

Decision:
앞으로도 영향을 미치는 과거 선택만 기록한다.

문서와 실제 코드가 다르면 어느 한쪽을 자동으로 정답 처리하지 말고
불일치와 근거를 명시한다.

────────────────
D. QA 상태 판별 및 migration
────────────────

QA를 다음 세 상태 중 하나로 판별해라.

A. .qa/manifest.yaml 존재:
- 이미 Contract v2다.
- qa-init을 다시 실행하지 말고 현재 manifest/runner/scenario를 확장한다.

B. QA 없음:
- Project OS가 정상 설치된 뒤 projectctl qa-init을 사용한다.

C. legacy QA 존재:
예:
- scripts/qa.ps1
- qa/
- schema_version: "1.0"
- UI_REVIEW_REQUIRED

이 경우:
- projectctl qa-init --force 금지
- 기존 QA runner를 먼저 분석
- build/test/smoke/screenshot 로직을 최대한 재사용
- .qa/manifest.yaml 추가
- .qa/scripts/run-qa.*로 entry point 정리
- result를 schemaVersion 2.0 형식으로 normalize
- v2가 실제로 통과한 뒤 legacy entry point 정리 여부를 검토

────────────────
E. 프로젝트별 QA Adapter
────────────────

repository의 실제 기술 스택을 기준으로 QA adapter를 설계한다.

특정 framework를 미리 가정하지 마라.

예:
Web:
- existing unit/e2e/browser stack

Android:
- existing Gradle/instrumentation/emulator harness

Windows/Game:
- existing build/process/smoke/screenshot harness

Chrome Extension:
- existing extension build + isolated browser context

CLI:
- command execution + exit/output assertions

이미 존재하는 도구를 새 framework로 교체하지 않는 것을 기본으로 한다.

Manifest에는 실제 지원 stage만 기록한다.

Scenario는 현재 구현되어 있고 자동 검증 가치가 높은 흐름부터 최소화해서 만든다.

QA runner는:
- caller runId 사용
- 실패해도 가능한 경우 result.json 생성
- 실행되지 않은 검증을 PASS 처리하지 않음
- child process cleanup
- repository-relative artifacts
- screenshot caption/kind/priority
- visualReviews 구조
를 준수해야 한다.

사람 판단이 필요한 기존 Human Gate는 자동화 성공처럼 숨기지 말고
HUMAN_GATE_REQUIRED로 연결한다.

────────────────
F. 기존 CI / Regression 보존
────────────────

Project OS/QA 도입 때문에 기존 CI를 제거하거나 대체하지 마라.

가능하면 기존 CI 위에 Contract validation 또는 QA smoke를 추가하는 방식으로 확장한다.

기존 test가 깨지면 도입 완료로 처리하지 마라.

────────────────
G. 검증
────────────────

가능한 범위에서 다음을 실행해라.

1. 기존 project tests
2. build/lint
3. projectctl doctor
4. projectctl status
5. projectctl next --role developer
6. QA runner
7. result.json v2 validation
8. artifact relative path validation
9. screenshot metadata validation
10. 기존 CI regression

이번 단계에서는 새로운 제품 기능을 구현하지 마라.
QA를 통과시키기 위해 unrelated product bug를 대규모로 수정하지 마라.
발견된 문제는 backlog/task로 분리할 수 있다.

제품 방향을 바꾸는 불확실성만 Human Gate로 남긴다.

마지막에 다음을 보고해라.

1. 도입 전 repository 상태
2. Project OS 기존/신규 여부
3. 완료/현재/미래 Milestone
4. 정리한 canonical state
5. 새 Backlog / Task
6. 기록한 Decision
7. QA 상태: none / v1 / v2
8. 재사용한 기존 test/QA 자산
9. 변경한 QA manifest/runner/scenario
10. 테스트/QA 결과
11. 발견된 문서-코드 불일치
12. Human Gate
13. 다음 실행 가능한 Task
```

---

# 4. 어떤 Prompt를 선택해야 하나

간단히 다음 기준으로 선택합니다.

```text
repository가 거의 비어 있음
또는 아직 본격 개발 전
    ↓
초기 세팅 Prompt

이미 기능/코드/문서/test/Git history가 있음
    ↓
프로젝트 중간 도입 Prompt
```

Project OS가 이미 설치되어 있더라도 QA만 나중에 붙이는 경우는 **프로젝트 중간 도입 Prompt**를 사용하면 됩니다. Prompt가 현재 `.project-os`와 `.qa` 상태를 먼저 판별하도록 되어 있으므로 중복 init을 피할 수 있습니다.

---

# 5. 세팅 완료 후 일상 작업 Prompt

초기/중간 도입이 끝난 뒤에는 긴 세팅 Prompt를 반복할 필요가 없습니다.

```text
현재 repository의 Project OS canonical state를 기준으로 다음 실행 가능한 작업을 진행해라.

시작 시:
1. AGENTS.md
2. PROJECT.md
3. .project-os/manifest.yaml
4. .project-os/state/current.yaml
5. 현재 Task와 필요한 reference

만 읽고 필요한 context를 복원해라.

projectctl doctor로 상태를 확인하고
projectctl next --role developer 기준 다음 Task를 선택해라.

구현 완료 전에는 configured quality gate와 QA를 수행해라.
.qa/manifest.yaml이 있으면 해당 Contract를 따라 QA를 실행하고,
FAIL을 완료로 처리하지 마라.

완료 후 evidence와 Project OS state를 갱신하고
다음 실행 가능한 Task를 보고해라.
```

이 방식의 목적은 프로젝트를 시작할 때만 긴 bootstrap/adoption Prompt를 사용하고, 이후에는 repository 안의 canonical state 자체가 다음 Agent 세션의 context가 되게 하는 것입니다.
