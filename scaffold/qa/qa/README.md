# Project QA

이 디렉터리는 Project OS 자동 QA Contract를 구현하기 위한 프로젝트별 영역입니다.

Project OS는 Playwright, Godot, Android ADB, Appium, pytest, Electron/Tauri 같은 특정 테스트 기술을 강제하지 않습니다. 실제 프로젝트가 필요한 도구를 선택하고 외부 인터페이스만 맞춥니다.

## 고정 Entry Point

Windows 우선 기본 진입점:

    .\scripts\qa.ps1

호출자가 run id를 지정할 수도 있습니다.

    .\scripts\qa.ps1 -RunId QA-manual-001

## 출력 위치

    .qa/
      runs/
        <run-id>/
          result.json
          stdout.log
          stderr.log
          screenshots/
          videos/
          artifacts/

result.json은 Project OS QA Result Contract 1.0을 따라야 합니다. Artifact path는 반드시 해당 run directory 기준의 forward-slash relative path여야 합니다.

## Stage

권장 순서:

    preflight
    → build
    → launch
    → smoke
    → functional
    → optional UI scenario
    → artifact collection
    → result.json
    → cleanup

지원하지 않는 단계는 SKIPPED로 남길 수 있습니다. 환경 문제로 테스트가 실행되지 못했다면 PASS로 기록하지 않습니다.

## Run status

- PASS: 자동 QA 통과, 별도 UI 검수 불필요
- FAIL: 테스트 실패, 환경 문제, QA 구성 오류 등으로 완료 불가
- UI_REVIEW_REQUIRED: 자동 검증은 통과했지만 사람의 시각 검수가 필요

UI_APPROVED와 UI_REJECTED는 이 contract의 상태가 아닙니다. Remote Control/Human Gate 계층에서 관리합니다.

## Exit code

- 0: PASS
- 1: FAIL
- 2: UI_REVIEW_REQUIRED

가능하면 실패 상황에서도 유효한 result.json을 먼저 생성한 뒤 종료하세요.

기본 scripts/qa.ps1은 안전을 위해 QA_NOT_CONFIGURED / FAIL을 반환하는 템플릿입니다. 프로젝트에 맞는 QA를 구현하기 전까지 성공으로 간주하면 안 됩니다.

## Scenario convention

qa/scenarios/*.yaml은 선택 사항입니다. 공통 DSL이 아니며 프로젝트별 runner가 읽는 가벼운 convention으로만 사용합니다.
