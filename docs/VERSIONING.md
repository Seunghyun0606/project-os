# Versioning

Project OS는 consumer project와 도구의 호환성을 명확히 하기 위해 서로 다른 버전을 분리합니다.

현재 기준:

| Version | Current | Meaning |
| --- | --- | --- |
| package | 0.3.0 | 설치된 projectctl Python package |
| scaffold | 0.3.0 | 새 프로젝트에 projectctl init으로 생성되는 base consumer scaffold |
| consumer schema | 1 | .project-os canonical data contract |
| QA result contract | 1.0 | .qa/runs/<run-id>/result.json contract |
| central DB schema | 1 | optional central SQLite operational store |

## Package version

projectctl 도구 자체의 버전입니다.

다음 세 위치는 항상 같은 값을 가져야 합니다.

- pyproject.toml
- VERSION
- projectctl.__version__

Package에 기능을 추가하되 기존 공개 동작을 깨지 않는 경우 minor version을 올립니다.

0.3.0에서는 optional QA scaffold 설치 기능과 qa-init command가 추가됩니다.

## Scaffold version

새 consumer project에 배포되는 base scaffold의 버전입니다.

.project-os/manifest.yaml의 project_os.scaffold_version에 기록합니다.

Scaffold version은 canonical schema 변경 없이도 다음 경우 올라갈 수 있습니다.

- 새 기본 디렉터리 추가
- 기본 AGENTS/PROJECT template 개선
- 새 workflow/runtime bootstrap 추가
- 기본 quality/context 설정 변경
- optional consumer overlay와 연동되는 기본 작업 규칙 추가

0.3.0에서는 consumer AGENTS에 optional QA completion rule이 추가되어 scaffold version도 0.3.0으로 올립니다.

QA 전용 파일은 scaffold/qa에 별도 overlay로 보관하며 기본 projectctl init에는 복사하지 않습니다.

## Consumer schema version

Git에 저장되는 canonical Project OS data contract의 버전입니다.

.project-os/manifest.yaml의 project_os.schema_version에 기록합니다.

0.3.0은 기존 canonical YAML 형식을 깨지 않으므로 consumer schema version은 1을 유지합니다.

Breaking canonical file-format change가 발생할 때만 consumer schema version을 올리고 ordered migration을 함께 제공합니다.

## QA result contract version

QA result contract는 consumer schema와 별개입니다.

현재 result.json의 schema_version은 1.0이며 repository의 schemas/qa-result.schema.json이 정의합니다.

이 버전은 다음 인터페이스를 보호합니다.

- run-level status
- stage status
- error metadata
- artifact metadata
- run-directory relative artifact path

UI_APPROVED/UI_REJECTED 같은 Remote Control Human Gate 상태는 이 schema에 포함하지 않습니다.

## Package compatibility

새 0.3.0 scaffold:

    project_os:
      scaffold_version: "0.3.0"
      schema_version: "1"
      package_compatibility: ">=0.3,<1.0"

기존 0.1.x/0.2.x consumer repository는 0.3.0 package로 계속 읽을 수 있습니다. 기존 consumer manifest나 scaffold를 자동으로 덮어쓰지 않습니다.

QA를 원하는 기존 Project OS 프로젝트는 전체 scaffold를 다시 설치하지 않고 다음 명령으로 optional overlay만 추가합니다.

    projectctl qa-init

## Upgrade rule

기존 consumer project를 최신 scaffold 전체 복사로 업그레이드하지 않습니다.

향후 projectctl upgrade는 다음 순서를 따라야 합니다.

1. package, scaffold, consumer schema version을 읽습니다.
2. 필요한 migration만 계산합니다.
3. Git에서 복구 가능한 상태인지 확인합니다.
4. 알려진 migration을 순서대로 적용합니다.
5. projectctl doctor를 실행합니다.
6. 알 수 없거나 손실 가능한 migration은 사람 승인 없이 진행하지 않습니다.

QA overlay는 canonical migration이 아닙니다. 사용자가 명시적으로 qa-init을 실행할 때만 설치합니다.

## Central control DB version

Phase 6의 SQLite control DB는 consumer schema와 별개의 runtime/operational database입니다.

현재 control DB schema version은 1이며 SQLite PRAGMA user_version으로 관리합니다.

중앙 DB가 유실되어도 consumer Git repository의 canonical project state는 유지되어야 합니다.

## Release checklist

- VERSION 업데이트
- pyproject.toml package version 업데이트
- projectctl.__version__ 업데이트
- consumer scaffold가 바뀌면 scaffold version 업데이트
- breaking canonical format change일 때만 consumer schema version 업데이트
- QA result contract가 바뀌면 QA schema_version 호환성 검토
- 새 scaffold의 package_compatibility 확인
- CHANGELOG.md 업데이트
- 전체 test 실행
- fresh base scaffold 생성 후 projectctl doctor 실행
- optional QA scaffold 설치/Windows PowerShell smoke test 실행
- README의 Quick start와 현재 command surface 확인
