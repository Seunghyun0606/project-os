# Versioning

Project OS는 consumer project와 도구의 호환성을 명확히 하기 위해 서로 다른 버전을 분리합니다.

현재 기준:

| Version | Current | Meaning |
| --- | --- | --- |
| package | 0.4.0 | 설치된 projectctl Python package |
| scaffold | 0.4.0 | 새 프로젝트에 projectctl init으로 생성되는 base consumer scaffold |
| consumer schema | 1 | .project-os canonical data contract |
| QA Contract | 2.0 | .qa/manifest.yaml / scenario / result contract |
| legacy QA result | 1.0 | 이전 scripts/qa.ps1 기반 result contract |
| central DB schema | 1 | optional central SQLite operational store |

## Package version

projectctl 도구 자체의 버전입니다.

다음 세 위치는 항상 같은 값을 가져야 합니다.

- pyproject.toml
- VERSION
- projectctl.__version__

0.4.0은 QA Contract v2, Manifest/Scenario schema, cross-platform QA scaffold를 추가합니다.

## Scaffold version

새 consumer project에 배포되는 base scaffold의 버전입니다.

`.project-os/manifest.yaml`의 `project_os.scaffold_version`에 기록합니다.

0.4.0에서는 consumer AGENTS의 QA completion rule이 v2 manifest 기반으로 변경되었습니다.

QA 전용 파일은 `scaffold/qa` optional overlay로 유지하며 일반 `projectctl init`에는 복사하지 않습니다.

## Consumer schema version

Git에 저장되는 canonical Project OS data contract의 버전입니다.

`.project-os/manifest.yaml`의 `project_os.schema_version`에 기록합니다.

0.4.0은 canonical project state format을 깨지 않으므로 consumer schema version은 1을 유지합니다.

## QA Contract version

QA Contract는 consumer canonical schema와 별개입니다.

현재 version은 2.0이며 다음 세 schema가 같은 Contract family를 정의합니다.

- schemas/qa-manifest.schema.json
- schemas/qa-scenario.schema.json
- schemas/qa-result.schema.json

v2는 v1 QA result와 breaking change입니다.

주요 차이:

- discovery point를 `.qa/manifest.yaml`로 고정
- Windows/Unix command를 Manifest가 제공
- result field naming을 camelCase로 정리
- PASS_WITH_WARNINGS / HUMAN_GATE_REQUIRED 추가
- stages/scenarios를 배열 구조로 일반화
- artifact path 기준을 repository-relative로 명시
- screenshot priority/kind metadata 추가
- visualReviews 구조 추가

이 breaking change는 consumer canonical schema migration이 아닙니다. QA overlay는 opt-in이며 기존 프로젝트 파일을 자동으로 덮어쓰지 않습니다.

Legacy v1 schema는 `schemas/qa-result-v1.schema.json`으로 보존합니다. Remote Control은 `schemaVersion` 또는 legacy `schema_version`을 보고 adapter를 선택할 수 있습니다.

## Package compatibility

새 0.4.0 scaffold:

```yaml
project_os:
  scaffold_version: "0.4.0"
  schema_version: "1"
  package_compatibility: ">=0.4,<1.0"
```

기존 0.1.x~0.3.x consumer repository는 0.4.0 package로 계속 읽을 수 있습니다. 기존 consumer manifest/scaffold/QA overlay를 자동으로 덮어쓰지 않습니다.

## Upgrade rule

기존 consumer project를 최신 scaffold 전체 복사로 업그레이드하지 않습니다.

향후 projectctl upgrade는 다음 순서를 따라야 합니다.

1. package, scaffold, consumer schema version을 읽습니다.
2. 필요한 migration만 계산합니다.
3. Git에서 복구 가능한 상태인지 확인합니다.
4. 알려진 migration을 순서대로 적용합니다.
5. projectctl doctor를 실행합니다.
6. 알 수 없거나 손실 가능한 migration은 사람 승인 없이 진행하지 않습니다.

QA v1 → v2는 프로젝트별 runner 구현과 함께 명시적으로 migration합니다. `projectctl qa-init --force`로 legacy QA 파일을 덮어쓰는 방식을 권장하지 않습니다.

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
- QA Contract가 바뀌면 QA schema version 및 legacy compatibility 검토
- 새 scaffold의 package_compatibility 확인
- CHANGELOG.md 업데이트
- 전체 test 실행
- fresh base scaffold 생성 후 projectctl doctor 실행
- optional QA scaffold Linux smoke 실행
- optional QA scaffold Windows PowerShell smoke 실행
- README의 Quick start와 현재 command surface 확인
