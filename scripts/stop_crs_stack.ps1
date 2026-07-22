$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ProcessFile = Join-Path $ProjectRoot "instance\crs_stack_processes.json"
$StatusFile = Join-Path $ProjectRoot "instance\plc_worker_status.json"
$LockFile = Join-Path $ProjectRoot "instance\plc_worker.lock"

if (Test-Path $ProcessFile) {
    try {
        $Info = Get-Content $ProcessFile -Raw | ConvertFrom-Json
        foreach ($PidValue in @($Info.web_pid, $Info.worker_pid)) {
            if ($PidValue) {
                Stop-Process -Id ([int]$PidValue) -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Host "Could not read CRS process file. Close the CRS windows manually." -ForegroundColor Yellow
    }
}

Remove-Item $ProcessFile -Force -ErrorAction SilentlyContinue
Remove-Item $StatusFile -Force -ErrorAction SilentlyContinue
Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
Write-Host "CRS web and PLC worker stop request completed." -ForegroundColor Green
