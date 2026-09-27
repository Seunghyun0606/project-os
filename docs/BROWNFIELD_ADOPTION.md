# Brownfield Adoption Guide

이미 개발이 진행 중인 프로젝트에 Project OS를 도입할 때는 신규 프로젝트처럼 과거 전체를 다시 작성하지 않습니다.

핵심 원칙은 다음과 같습니다.

> **과거는 요약하고, 현재는 정확히 복원하고, 미래부터 Project OS로 상세 관리한다.**

## 1. 도입 목표

기존 프로젝트의 코드, 문서, Git history, TODO를 유지한 채 Project OS의 canonical state를 구성하는 것이 목적입니다.

~~~text
기존 프로젝트
  ├─ 코드
  ├─ README / docs / specs
  ├─ 기존 TODO
  ├─ Git history
  └─ 현재 진행 작업
        ↓
Project OS adoption
        ↓
PROJECT.md
.project-os/state/roadmap.yaml
.project-os/state/backlog.yaml
.project-os/state/current.yaml
.project-os/tasks/
.project-os/decisions/
        ↓
이후 작업부터 Project OS로 관리
~~~

과거 작업을 전부 Task history로 재구성하는 것은 목표가 아닙니다.

## 2. 별도 branch에서 시작

기존 프로젝트에 도입할 때는 먼저 별도 branch를 권장합니다.

~~~bash
git checkout -b chore/adopt-project-os
~~~

그 다음 프로젝트 루트에서:

~~~bash
projectctl init
~~~

projectctl init은 기존 scaffold 대상 파일과 충돌하는 경우 덮어쓰지 않고 중단합니다.

기존 PROJECT.md, AGENTS.md 등이 이미 있다면 내용을 먼저 비교하고 병합하세요. 기존 프로젝트에서는 충돌을 무시하기 위해 --force로 덮어쓰는 방식보다 수동 병합을 권장합니다.

## 3. 기존 문서는 원본을 유지

기존 문서를 Project OS 도입을 위해 모두 이동하거나 다시 작성할 필요는 없습니다.

예:

~~~text
README.md
docs/
architecture.md
requirements.md
TODO.md
~~~

필요한 경우에만 점진적으로 specs/ 구조로 정리합니다.

~~~text
specs/
├─ product/
├─ feature/
├─ architecture/
└─ ux/
~~~

Task에서는 기존 문서를 reference로 연결할 수 있습니다.

~~~yaml
references:
  - docs/auth-design.md
  - docs/api-spec.md
~~~

## 4. 먼저 Repository Inventory를 수행

중간 도입에서 가장 중요한 단계입니다.

새 기능을 바로 구현하지 말고 먼저 현재 저장소의 실제 상태를 조사합니다.

확인 대상:

- 현재 제품 목적과 주요 기능
- 구현 완료된 기능
- 진행 중 기능
- 미완료 기능
- README / docs / specs
- 기존 TODO / issue / task 문서
- 주요 source directory
- test / CI 구성
- 현재 branch와 최근 Git history
- 앞으로도 유효한 아키텍처 결정
- 문서와 코드의 불일치

흐름:

~~~text
Repository Inventory
        ↓
As-Is 정리
        ↓
문서 / 코드 / TODO 간 Gap 분석
        ↓
Project OS canonical state 구성
~~~

## 5. PROJECT.md 복원

기존 README, 기획서, 코드와 설계 문서에서 앞으로도 유지해야 할 장기 방향만 추출합니다.

권장 내용:

- Vision
- Target User
- Core Experience
- Product Principles
- Architecture Constraints
- Non-goals
- Success Definition

현재 진행 상황이나 세부 TODO는 PROJECT.md에 넣지 않습니다.

~~~text
PROJECT.md
→ 무엇을 만드는가
→ 왜 만드는가
→ 핵심 원칙은 무엇인가
→ 쉽게 바꾸면 안 되는 제약은 무엇인가
~~~

현재 상태는 .project-os/state/current.yaml이 담당합니다.

## 6. 과거 작업은 Milestone 수준으로 복원

이미 완료된 개발을 과거 Task로 전부 역생성하지 않습니다.

예:

~~~text
M1 Foundation       completed
M2 Core MVP         completed
M3 Integration      active
M4 Production QA    planned
~~~

필요하면 완료된 Milestone에 짧은 summary만 남깁니다.

세부 과거 Task를 복원해야 하는 경우는 다음과 같이 명확한 가치가 있을 때만 권장합니다.

- 추적이 필요한 규제/감사 근거
- 중요한 설계 결정의 provenance
- 현재 작업의 dependency 분석에 꼭 필요한 이력
- 회귀 테스트 기준을 만들기 위해 필요한 과거 acceptance criteria

## 7. Backlog는 앞으로 할 일 중심으로 구성

기존 TODO를 그대로 Project OS Task로 복사하지 않습니다.

~~~text
기존 TODO
- 로그인 개선
- 테스트 추가
- 배포 수정
~~~

먼저 실제 코드와 문서를 확인한 뒤 다음처럼 정규화합니다.

~~~text
로그인 개선
    ↓
현재 구현 확인
    ↓
문제 정의
    ↓
scope / acceptance criteria / verification 정의
    ↓
canonical Task 생성
~~~

.project-os/state/backlog.yaml에는 앞으로 실제 수행할 작업을 중심으로 등록합니다.

## 8. Task는 현재와 미래 작업만 상세화

현재 진행 중이거나 다음에 실행 가능한 작업부터 canonical Task contract를 만듭니다.

~~~text
.project-os/tasks/
~~~

Task에는 최소 다음 내용을 포함하는 것을 권장합니다.

- goal
- rationale
- include / exclude scope
- references
- acceptance criteria
- verification
- dependencies

기존 자유형 작업 문서는 원본을 유지하고 Task의 references에서 연결합니다.

## 9. 기존 결정은 필요한 것만 Decision으로 승격

과거의 모든 기술 선택을 Decision으로 만들 필요는 없습니다.

앞으로의 구현과 운영에 계속 영향을 미치는 결정만 .project-os/decisions/에 기록합니다.

예:

- DB 종류
- 인증 방식
- public API compatibility 정책
- 특정 framework를 유지해야 하는 이유
- 데이터 migration 원칙
- 운영상 변경 금지 제약

## 10. 문서와 코드가 다를 때

Brownfield 프로젝트에서는 문서와 실제 코드가 불일치할 수 있습니다.

둘 중 하나를 자동으로 정답으로 간주하지 않습니다.

1. 불일치를 기록한다.
2. 실제 runtime behavior가 무엇인지 확인한다.
3. 사용자 의도 또는 최신 결정이 명확하면 canonical 문서를 수정한다.
4. 제품 방향을 바꾸는 불확실성만 Human Gate로 남긴다.

## 11. 권장 최초 Codex Prompt

~~~text
이 저장소는 이미 개발이 진행 중인 기존 프로젝트이며,
지금부터 Project OS를 도입한다.

이번 작업의 목적은 새로운 기능을 구현하는 것이 아니라,
현재 저장소의 실제 상태를 분석해서 Project OS의 canonical state를 구성하는 것이다.

먼저 다음을 확인해라.

1. AGENTS.md
2. PROJECT.md
3. README.md
4. 기존 docs/, specs/ 및 기획/설계 문서
5. 현재 Git branch와 최근 commit history
6. 주요 source directory
7. 기존 TODO / issue / task 관련 파일
8. test / CI 구성
9. .project-os/ 현재 상태

그 다음 repository를 분석해서 다음을 수행해라.

1. 현재 제품의 목적과 장기 원칙을 추출해 PROJECT.md를 정리한다.

2. 이미 완료된 주요 개발 단계를 식별하여
   .project-os/state/roadmap.yaml의 completed milestone으로 기록한다.

3. 현재 진행 중인 milestone을 식별한다.

4. 기존 TODO, 코드 상태, 문서, 테스트 상태를 비교해서
   앞으로 실제 수행해야 할 작업만 backlog.yaml에 생성한다.

5. 이미 완료된 세부 작업을 과거 Task로 전부 역생성하지 않는다.
   필요하면 milestone summary 수준으로만 기록한다.

6. 현재 진행 중이거나 다음에 실행 가능한 작업에 대해서만
   .project-os/tasks/에 canonical Task contract를 생성한다.

7. 기존 자유형 기획/요구사항/설계 문서는 원본을 유지하고
   필요한 Task의 references로 연결한다.

8. 코드와 문서에서 확인된 중요한 아키텍처 결정 중
   앞으로도 영향을 미치는 사항은 .project-os/decisions/에 기록한다.

9. 문서와 실제 코드가 다르면 코드를 무조건 정답으로 간주하지 말고,
   불일치를 명시적으로 기록한다.

10. 제품 방향을 바꾸는 수준의 불확실성만 Human Gate로 남긴다.

11. projectctl doctor를 실행하고 Project OS 구조 오류를 수정한다.

이번 단계에서는 새로운 기능을 구현하거나 리팩터링하지 마라.

마지막에 다음을 보고한다.

- 현재 프로젝트 상태 요약
- 완료된 Milestone
- 현재 Milestone
- 새로 구성한 Backlog
- 다음 실행 가능한 Task
- 발견된 문서/코드 불일치
- Human Gate
~~~

## 12. Adoption 완료 기준

도입 작업이 끝났을 때는 다음 상태가 이상적입니다.

~~~text
기존 코드                  유지
기존 문서                  유지

PROJECT.md                 장기 방향 반영
specs/                     필요한 것만 점진적 정리

.project-os/
├─ state/
│  ├─ roadmap.yaml         과거 완료 + 현재 + 미래
│  ├─ backlog.yaml         앞으로 할 일 중심
│  └─ current.yaml         지금 위치
├─ tasks/                  현재/다음 작업
└─ decisions/              앞으로도 유효한 결정
~~~

그리고 다음 명령이 정상 동작해야 합니다.

~~~bash
projectctl status
projectctl doctor
projectctl next --role developer
~~~

## 운영 원칙 요약

~~~text
과거
→ 완벽하게 재현하지 않는다.
→ 중요한 Milestone / Decision만 보존한다.

현재
→ 코드, 문서, TODO, test 상태를 비교해 정확히 복원한다.

미래
→ Project OS Task / evidence / quality gate로 상세 관리한다.
~~~

Project OS 도입일을 상세 실행 이력의 시작점으로 삼는 것이 가장 단순하고 유지보수하기 좋습니다.
