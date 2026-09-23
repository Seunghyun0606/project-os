# Project OS

Project OS는 AI 에이전트가 프로젝트의 방향과 현재 상태를 잃지 않고 장기간 작업할 수 있도록 돕는 **프로젝트 관리 scaffold + 도구**입니다.

목표는 매 세션마다 긴 프롬프트를 다시 설명하지 않아도, 프로젝트 저장소 안의 상태·계획·작업 기준을 읽고 이어서 일할 수 있게 하는 것입니다.

> Remote 실행, 메신저 제어, Lightsail/Desktop 라우팅은 이 저장소의 책임이 아닙니다. 별도 Remote Control 프로젝트에서 다룹니다.

## 개요

Project OS는 두 부분으로 나뉩니다.

- **scaffold/**: 다른 프로젝트에 넣어서 바로 사용하는 최소 파일 세트
- **projectctl**: scaffold를 만들고, 상태를 확인하고, 다음 작업을 선택하고, 파일 간 일관성을 검사하는 도구

Project OS 자체를 개발하기 위한 코드, 테스트, 스키마, 버전 문서는 다른 프로젝트로 복사되지 않습니다.

```text
project-os/                  # 이 저장소
├─ scaffold/                 # 다른 프로젝트가 가져가는 영역
├─ src/projectctl/           # Project OS 도구 구현
├─ defaults/                 # 공통 역할/품질/컨텍스트 기본값
├─ schemas/                  # Project OS 파일 검증 규칙
├─ docs/                     # Project OS 자체 문서
└─ tests/                    # Project OS 자체 테스트

your-project/                # 실제 사용하는 프로젝트
├─ PROJECT.md
├─ AGENTS.md
├─ specs/
└─ .project-os/
```

## Quick start

### 1. Project OS 설치

개발 중에는 이 저장소를 clone한 뒤 editable install을 권장합니다.

```bash
git clone https://github.com/Seunghyun0606/project-os.git
cd project-os
python -m pip install -e .
```

설치 확인:

```bash
projectctl version
# 0.2.0
```

### 2. 기존 프로젝트에 scaffold 추가

사용할 프로젝트 루트에서:

```bash
projectctl init
```

생성되는 핵심 파일:

```text
PROJECT.md
AGENTS.md
specs/
.project-os/
├─ manifest.yaml
├─ profile.yaml
├─ state/
│  ├─ current.yaml
│  ├─ roadmap.yaml
│  └─ backlog.yaml
├─ tasks/
├─ decisions/
├─ quality/
│  └─ gates.yaml
├─ context/
│  └─ index.yaml
├─ workflows/
└─ runs/
   ├─ summaries/
   └─ runtime/
```

작업 중 필요한 빈 디렉터리도 함께 준비됩니다.

### 3. 프로젝트 기획 입력

먼저 `PROJECT.md`에 다음 내용을 적습니다.

- 무엇을 만드는지
- 누구를 위한 것인지
- 가장 중요한 사용자 경험
- 이번 프로젝트에서 하지 않을 것
- 중요한 제품/기술 원칙

그 다음 `.project-os/state/roadmap.yaml`에 큰 단계(Milestone)를 정의하고, `backlog.yaml`에 작업을 추가합니다.

### 4. 상태 확인

```bash
projectctl status
projectctl doctor
```

다음 개발 작업 확인:

```bash
projectctl next --role developer
```

### 5. Codex에서 사용

새 세션에서도 저장소 루트의 `AGENTS.md`를 시작점으로 사용합니다.

일반적으로 사용자는 길게 설명할 필요 없이 다음과 같이 요청할 수 있습니다.

```text
현재 Project OS 상태를 기준으로 다음 작업을 계속 진행해.
```

에이전트는 `PROJECT.md → .project-os/manifest.yaml → 현재 상태 → 현재 Task` 순서로 필요한 정보만 읽습니다.

---

## 상세 가이드

### PROJECT.md

프로젝트에서 가장 오래 유지되는 방향을 기록합니다.

여기에는 일시적인 진행 상황보다 다음 내용을 둡니다.

- Vision
- Target user
- Core experience
- Product principles
- Non-goals
- Success definition

### .project-os/state/current.yaml

현재 위치만 기록하는 짧은 snapshot입니다.

예:

```yaml
project_status: active
current_milestone: M1
current_tasks: []
blocked_tasks: []
human_gate: false
```

긴 작업 기록이나 대화 내용은 넣지 않습니다.

### Roadmap과 Milestone

`roadmap.yaml`은 프로젝트의 큰 작업 순서를 관리합니다.

Milestone 상세 정의는 `.project-os/milestones/` 아래에 추가합니다. 각 Milestone에는 완료 기준을 명확히 적는 것을 권장합니다.

### Backlog와 Task

`backlog.yaml`은 전체 작업의 상태와 우선순위를 관리합니다.

실제 작업 계약은 `.project-os/tasks/`에 둡니다.

Task에는 최소한 다음 정보가 있어야 합니다.

- 목표
- 왜 필요한지
- 포함 범위 / 제외 범위
- 참고할 spec
- 완료 조건
- 검증 방법
- 선행 Task

### Specs

상세 기획과 기술 설계는 `specs/` 아래에 둡니다.

```text
specs/
├─ product/
├─ feature/
├─ architecture/
└─ ux/
```

Project OS의 상태 파일과 상세 기획서를 분리하면 현재 상태를 읽기 위해 긴 문서를 매번 읽는 일을 줄일 수 있습니다.

### 품질 기준

`.project-os/quality/gates.yaml`은 작업을 완료로 볼 수 있는 최소 기준을 정합니다.

예를 들어 프로젝트에 따라 build, lint, unit test, integration test, 독립 review 등을 필수로 지정할 수 있습니다.

### Human Gate

사람의 판단이 꼭 필요한 경우만 중단하도록 합니다.

권장 예:

- 제품 방향 변경
- Milestone 범위 변경
- 호환성을 깨는 아키텍처 변경
- 데이터 삭제
- 운영 배포
- 최종 디자인 승인

단순 구현 선택, 테스트 작성, 명확한 버그 수정은 기본적으로 Agent가 계속 진행할 수 있도록 합니다.

### 장기 작업과 세션 변경

Project OS는 대화 세션을 장기 기억으로 사용하지 않습니다.

```text
대화/세션 = 일시적인 작업 공간
Git + PROJECT.md + .project-os = 프로젝트의 장기 기억
```

새 세션이나 다른 모델이 시작하더라도 저장소의 정본을 읽어 현재 상태를 복구할 수 있어야 합니다.

### projectctl 주요 명령

```bash
projectctl init                 # scaffold 설치
projectctl version              # Project OS 버전
projectctl status               # 현재 상태
projectctl doctor               # 구조/참조 일관성 검사
projectctl next --role developer # 다음 실행 가능한 Task
projectctl context TASK-001     # 역할별 정책 + token budget가 적용된 Task context package
projectctl claim TASK-001       # Task 선점
projectctl submit TASK-001 FILE # 구조화된 작업 결과 제출
projectctl compact-runs --keep-recent 20 # 오래된 run 기록 요약/보관
projectctl role-policy developer # 역할별 권한 확인
projectctl review TASK-001 review.yaml --actor reviewer-1
projectctl record-test TASK-001 tests.yaml --actor ci
projectctl qa TASK-001 qa.yaml --actor qa-1
projectctl evaluate TASK-001 evaluation.yaml --actor evaluator-1
projectctl runtime-status run-001
projectctl approval-status approval-...
projectctl approval-resolve approval-... approved
projectctl control register /path/to/project
projectctl control dashboard
```

context package는 역할별 기본 정책과 프로젝트 override를 합쳐 필요한 spec·파일·활성 Decision·선행 Task 결과 요약만 읽습니다. 전체 저장소를 기본으로 스캔하지 않으며 역할별 token budget을 넘으면 deterministic하게 잘라냅니다.

`projectctl doctor`는 구조/Task dependency뿐 아니라 manifest의 package compatibility도 확인합니다.

오래된 실행 기록은 `.project-os/runs/history/`에 계속 쌓아두지 않고 `projectctl compact-runs`로 정리할 수 있습니다. 최근 실행만 남기고, 오래된 실행은 작은 구조화 요약을 `runs/summaries/history.yaml`에 남긴 뒤 원본을 `runs/archive/`로 이동합니다. 원본을 삭제하지 않으므로 Git에서 검증 근거를 계속 추적할 수 있습니다. 자세한 형식은 `docs/RUN_HISTORY.md`를 참고하세요.

Phase 3부터 worker 결과와 승인 결과를 분리합니다. `submit`은 implementation handoff만 저장하며 Task를 완료하지 않습니다. reviewer/QA/evaluator는 별도 handoff를 기록하고, 최종 상태 변경은 `evaluate`를 통해 single-writer state transition으로만 수행됩니다. 같은 actor가 자신의 implementation을 review/evaluate하는 것은 차단됩니다. 자세한 내용은 `docs/ROLES_AND_HANDOFFS.md`를 참고하세요.

Phase 4의 native orchestrator는 workflow 실행을 checkpoint 단위로 재개할 수 있습니다. 실행 중 checkpoint/event/approval은 `.project-os/runs/runtime/`에만 저장되며 canonical backlog/state를 직접 수정하지 않습니다. 따라서 orchestration backend를 교체해도 프로젝트 정본은 그대로 유지됩니다. 자세한 내용은 `docs/ORCHESTRATION.md`를 참고하세요.

Phase 5에서는 CLI와 다른 Agent harness가 같은 규칙을 사용하도록 `ProjectService`를 공통 진입점으로 둡니다. MCP 쪽도 별도 상태 변경 로직을 갖지 않고 이 service를 호출하는 얇은 adapter만 제공합니다. 자동 테스트 결과는 implementation과 별도 evidence로 기록됩니다. 자세한 내용은 `docs/MULTI_HARNESS.md`를 참고하세요.

여러 Project OS 저장소를 함께 관리해야 할 때는 `projectctl control`을 사용할 수 있습니다. 중앙 DB는 프로젝트 등록 정보, 실행 상태, 비용, 평가 이력 같은 요약 정보만 관리하며 backlog·spec·decision의 정본을 가져가지 않습니다. 기본 DB는 저장소 밖의 `~/.project-os/control.db`입니다. 자세한 내용은 `docs/CENTRAL_CONTROL.md`를 참고하세요.

Project OS core는 특정 LLM 실행기나 orchestration framework에 종속되지 않습니다. MCP는 현재 얇은 adapter로 제공하며, LangGraph·Agents SDK 같은 framework는 실제 필요가 생길 때 동일한 core contract 위에 adapter로 추가합니다. Remote Worker와 메신저/호스트 제어는 계속 별도 시스템의 책임입니다.

## Scaffold와 Project OS 개발 파일 구분

**다른 프로젝트가 가져가는 것은 `scaffold/default/`의 내용뿐입니다.**

다음은 Project OS 자체를 개발하기 위한 파일이며 대상 프로젝트에 복사하지 않습니다.

- `src/`
- `defaults/`
- `schemas/`
- `docs/`
- `tests/`
- `CHANGELOG.md`
- `VERSION`
- `pyproject.toml`

`projectctl init`이 이 구분을 자동으로 지킵니다.

## 버전 관리

Project OS는 package, scaffold, schema version을 구분합니다.

| 구분 | 현재 | 의미 |
| --- | --- | --- |
| package | `0.2.0` | `projectctl` 도구 버전 |
| scaffold | `0.2.0` | 새 프로젝트에 생성되는 scaffold 버전 |
| schema | `1` | canonical `.project-os` 데이터 형식 |

새 0.2.0 scaffold는 `projectctl >=0.2,<1.0`을 요구합니다. 기존 0.1.x consumer repository는 0.2.0 package로 계속 읽을 수 있으며, 기존 프로젝트에 최신 scaffold를 통째로 덮어쓰지 않습니다.

Phase 6의 중앙 SQLite DB schema는 consumer schema와 별도로 관리되며 현재 version은 `1`입니다.

자세한 호환성과 upgrade 원칙은 `docs/VERSIONING.md`를 참고하세요.

## 설계 원칙

- 프로젝트 기억은 Git에 남긴다.
- Agent 개인 기억보다 프로젝트 정본을 신뢰한다.
- 전체 저장소를 매번 읽지 않는다.
- LLM이 필요 없는 판단은 코드로 처리한다.
- Agent는 자기 작업을 스스로 승인하지 않는다.
- 작업 완료는 설정된 evidence와 quality gate로 판단한다.
- 특정 모델, Codex, LangGraph에 Project OS 자체를 종속시키지 않는다.
- Remote 실행과 메신저 제어는 별도 시스템의 책임으로 둔다.
