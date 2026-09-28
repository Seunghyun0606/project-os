[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$RunId
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = "QA-{0}-{1}" -f ([DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssfff")), $PID
}

if ($RunId -notmatch '^QA-[A-Za-z0-9][A-Za-z0-9._-]*$') {
    throw "RunId must match QA-[A-Za-z0-9][A-Za-z0-9._-]*"
}

$runDir = Join-Path $projectRoot (".qa\runs\" + $RunId)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "screenshots") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "videos") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "artifacts") | Out-Null

$startedAt = [DateTime]::UtcNow.ToString("o")
$projectName = "__PROJECT_ID__"
$stdoutPath = Join-Path $runDir "stdout.log"
$stderrPath = Join-Path $runDir "stderr.log"

@(
    "Project OS QA scaffold is installed."
    "This template is intentionally not a project-specific QA implementation."
    "Replace this result with real preflight/build/launch/test/artifact/cleanup logic."
) | Set-Content -Path $stdoutPath -Encoding UTF8

@(
    "QA_NOT_CONFIGURED: scripts/qa.ps1 must be implemented for this project before QA can pass."
) | Set-Content -Path $stderrPath -Encoding UTF8

$result = [ordered]@{
    schema_version = "1.0"
    run_id = $RunId
    project = $projectName
    status = "FAIL"
    started_at = $startedAt
    finished_at = [DateTime]::UtcNow.ToString("o")
    preflight = "FAIL"
    build = "SKIPPED"
    launch = "SKIPPED"
    smoke = "SKIPPED"
    functional = "SKIPPED"
    ui = "SKIPPED"
    artifact_collection = "PASS"
    cleanup = "SKIPPED"
    next_action = "FIX_AND_RETRY"
    recommendation = "Implement project-specific QA in scripts/qa.ps1. Keep the Project OS result contract unchanged."
    errors = @(
        [ordered]@{
            code = "QA_NOT_CONFIGURED"
            message = "The optional QA scaffold is installed but project-specific QA has not been implemented."
            stage = "preflight"
            kind = "configuration"
            retryable = $false
        }
    )
    artifacts = @(
        [ordered]@{ type = "log"; name = "stdout"; path = "stdout.log" },
        [ordered]@{ type = "log"; name = "stderr"; path = "stderr.log" }
    )
}

$resultPath = Join-Path $runDir "result.json"
$result | ConvertTo-Json -Depth 10 | Set-Content -Path $resultPath -Encoding UTF8
Write-Host "QA result: $resultPath"
exit 1
