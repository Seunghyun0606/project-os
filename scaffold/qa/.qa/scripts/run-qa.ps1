[CmdletBinding()]
param([Parameter(Mandatory = $false)][string]$RunId)

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Content)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

$qaRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $qaRoot
if ([string]::IsNullOrWhiteSpace($RunId)) {
    $RunId = "QA-{0}-{1}" -f ([DateTime]::UtcNow.ToString("yyyyMMdd-HHmmssfff")), $PID
}
if ($RunId -notmatch '^QA-[A-Za-z0-9][A-Za-z0-9._-]*$') {
    throw "RunId must match QA-[A-Za-z0-9][A-Za-z0-9._-]*"
}

$relativeRunDir = ".qa/runs/$RunId"
$runDir = Join-Path $projectRoot (".qa\runs\" + $RunId)
$logsDir = Join-Path $runDir "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "screenshots") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "visual") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $runDir "metadata") | Out-Null

$startedAt = [DateTime]::UtcNow.ToString("o")
Write-Utf8NoBom -Path (Join-Path $logsDir "stdout.log") -Content "Project OS QA Contract v2 scaffold is installed."
Write-Utf8NoBom -Path (Join-Path $logsDir "stderr.log") -Content "QA_NOT_CONFIGURED: implement project-specific QA in .qa/scripts/run-qa.ps1."

$result = [ordered]@{
    schemaVersion = "2.0"
    runId = $RunId
    project = [ordered]@{ id = "__PROJECT_ID__"; name = "__PROJECT_NAME__" }
    status = "FAIL"
    startedAt = $startedAt
    finishedAt = [DateTime]::UtcNow.ToString("o")
    summary = [ordered]@{ total = 1; passed = 0; failed = 1; warnings = 0; skipped = 0; humanGates = 0 }
    stages = @([ordered]@{ id = "preflight"; status = "FAIL"; message = "Project-specific QA runner is not configured." })
    scenarios = @()
    artifacts = @(
        [ordered]@{ type = "log"; name = "stdout"; path = "$relativeRunDir/logs/stdout.log"; stage = "preflight" },
        [ordered]@{ type = "log"; name = "stderr"; path = "$relativeRunDir/logs/stderr.log"; stage = "preflight"; severity = "error" }
    )
    visualReviews = @()
    errors = @([ordered]@{
        code = "QA_NOT_CONFIGURED"
        message = "The QA scaffold is installed but project-specific QA has not been implemented."
        stage = "preflight"
        kind = "configuration"
        retryable = $false
    })
    nextAction = "FIX_AND_RETRY"
}

$resultPath = Join-Path $runDir "result.json"
Write-Utf8NoBom -Path $resultPath -Content ($result | ConvertTo-Json -Depth 12)
Write-Host "QA result: $resultPath"
exit 1
