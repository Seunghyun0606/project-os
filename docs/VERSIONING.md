# Versioning

Project OS는 consumer project와 도구의 호환성을 명확히 하기 위해 세 가지 버전을 분리합니다.

현재 기준:

| Version | Current | Meaning |
| --- | --- | --- |
| package | `0.3.0` | 설치된 `projectctl` Python package |
| scaffold | `0.2.0` | 새 프로젝트에 `projectctl init`으로 생성되는 consumer scaffold |
| schema | `1` | `.project-os` canonical data contract |

## Package version

`projectctl` 도구 자체의 버전입니다.

다음 세 위치는 항상 같은 값을 가져야 합니다.

- `pyproject.toml`
- `VERSION`
- `projectctl.__version__`

Package에 기능을 추가하되 기존 공개 동작을 깨지 않는 경우 minor version을 올립니다. Persistent Project Session 기능은 이 규칙에 따라 package 0.3.0으로 추가되며 scaffold 0.2.0은 그대로 유지합니다.

## Scaffold version

새 consumer project에 배포되는 bootstrap/scaffold의 버전입니다.

`.project-os/manifest.yaml`의 `project_os.scaffold_version`에 기록합니다.

Scaffold version은 다음과 같은 경우 schema 변경 없이도 올라갈 수 있습니다.

- 새 기본 디렉터리 추가
- 기본 AGENTS/PROJECT template 개선
- 새 workflow/runtime bootstrap 추가
- 기본 quality/context 설정 변경

0.2.0에서는 workflow/runtime 디렉터리가 scaffold에 추가됐기 때문에 scaffold version도 0.2.0으로 올립니다.

## Schema version

Git에 저장되는 canonical Project OS data contract의 버전입니다.

`.project-os/manifest.yaml`의 `project_os.schema_version`에 기록합니다.

현재 0.3.0 package도 기존 canonical YAML 형식을 깨지 않으므로 schema version은 `1`을 유지합니다.

Breaking file-format change가 발생할 때만 schema version을 올리고, 반드시 ordered migration을 함께 제공합니다.

## Package compatibility

Consumer manifest의 `package_compatibility`는 해당 scaffold를 안전하게 다룰 수 있는 `projectctl` 범위를 선언합니다.

새 0.2.0 scaffold:

```yaml
project_os:
  scaffold_version: "0.2.0"
  schema_version: "1"
  package_compatibility: ">=0.2,<1.0"
```

기존 0.1.x/0.2.x consumer repository를 0.3.0 package로 읽는 것은 호환됩니다. 기존 manifest를 새 scaffold로 덮어쓰지 않습니다.

## Upgrade rule

기존 consumer project를 최신 scaffold 전체 복사로 업그레이드하지 않습니다.

향후 `projectctl upgrade`는 다음 순서를 따라야 합니다.

1. package, scaffold, schema version을 읽습니다.
2. 필요한 migration만 계산합니다.
3. Git에서 복구 가능한 상태인지 확인합니다.
4. 알려진 migration을 순서대로 적용합니다.
5. `projectctl doctor`를 실행합니다.
6. 알 수 없거나 손실 가능한 migration은 사람 승인 없이 진행하지 않습니다.

## Central control DB version

Phase 6의 SQLite control DB는 consumer schema와 별개의 runtime/operational database입니다.

현재 control DB schema version은 `2`이며 SQLite `PRAGMA user_version`으로 관리합니다. v1→v2는 `sessions`와 `jobs`를 추가하는 ordered migration이며 consumer canonical schema version `1`은 변경하지 않습니다.

이 버전은 package/scaffold/schema 세 버전과 별개입니다. 중앙 DB가 유실되어도 consumer Git repository의 canonical project state는 유지되어야 합니다.

## Release checklist

- `VERSION` 업데이트
- `pyproject.toml` package version 업데이트
- `projectctl.__version__` 업데이트
- consumer scaffold가 바뀌면 scaffold version 업데이트
- breaking canonical format change일 때만 schema version 업데이트
- 새 scaffold의 `package_compatibility` 확인
- `CHANGELOG.md` 업데이트
- 전체 test 실행
- fresh scaffold 생성 후 `projectctl doctor` 실행
- README의 Quick start와 현재 command surface 확인
