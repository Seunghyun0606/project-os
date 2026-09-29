#!/usr/bin/env sh
set -eu

RUN_ID=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-id) RUN_ID="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 64 ;;
  esac
done

if [ -z "$RUN_ID" ]; then
  RUN_ID="QA-$(date -u +%Y%m%d-%H%M%S)-$$"
fi

case "$RUN_ID" in
  QA-*) ;;
  *) echo "RunId must start with QA-." >&2; exit 64 ;;
esac
SAFE_ID=$(printf '%s' "$RUN_ID" | sed 's/^QA-//')
case "$SAFE_ID" in
  ""|*[!A-Za-z0-9._-]*) echo "RunId contains unsupported characters." >&2; exit 64 ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
QA_ROOT=$(dirname "$SCRIPT_DIR")
PROJECT_ROOT=$(dirname "$QA_ROOT")
RUN_DIR="$PROJECT_ROOT/.qa/runs/$RUN_ID"
LOGS_DIR="$RUN_DIR/logs"
mkdir -p "$LOGS_DIR" "$RUN_DIR/screenshots" "$RUN_DIR/visual" "$RUN_DIR/metadata"

printf '%s\n' "Project OS QA Contract v2 scaffold is installed." > "$LOGS_DIR/stdout.log"
printf '%s\n' "QA_NOT_CONFIGURED: implement project-specific QA in .qa/scripts/run-qa.sh." > "$LOGS_DIR/stderr.log"
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
FINISHED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$RUN_DIR/result.json" <<EOF
{
  "schemaVersion": "2.0",
  "runId": "$RUN_ID",
  "project": {"id": "__PROJECT_ID__", "name": "__PROJECT_NAME__"},
  "status": "FAIL",
  "startedAt": "$STARTED_AT",
  "finishedAt": "$FINISHED_AT",
  "summary": {"total": 1, "passed": 0, "failed": 1, "warnings": 0, "skipped": 0, "humanGates": 0},
  "stages": [{"id": "preflight", "status": "FAIL", "message": "Project-specific QA runner is not configured."}],
  "scenarios": [],
  "artifacts": [
    {"type": "log", "name": "stdout", "path": ".qa/runs/$RUN_ID/logs/stdout.log", "stage": "preflight"},
    {"type": "log", "name": "stderr", "path": ".qa/runs/$RUN_ID/logs/stderr.log", "stage": "preflight", "severity": "error"}
  ],
  "visualReviews": [],
  "errors": [{"code": "QA_NOT_CONFIGURED", "message": "The QA scaffold is installed but project-specific QA has not been implemented.", "stage": "preflight", "kind": "configuration", "retryable": false}],
  "nextAction": "FIX_AND_RETRY"
}
EOF

echo "QA result: $RUN_DIR/result.json"
exit 1
