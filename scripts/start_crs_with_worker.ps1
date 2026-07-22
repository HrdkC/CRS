$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$StatusFile = Join-Path $ProjectRoot "instance\plc_worker_status.json"
$ProcessFile = Join-Path $ProjectRoot "instance\crs_stack_processes.json"

if (-not (Test-Path $PythonExe)) {
    throw "CRS virtual environment not found: $PythonExe"
}

Write-Host ""
Write-Host "CRS Web + Durable PLC Worker Launcher" -ForegroundColor Cyan
Write-Host "This starts live PLC communication for queued Restore/Save/Upload/Download operations." -ForegroundColor Yellow
$Confirmation = Read-Host "Type START to continue"
if ($Confirmation -cne "START") {
    Write-Host "Cancelled. No process was started." -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Force (Join-Path $ProjectRoot "instance") | Out-Null

$WorkerAlreadyOnline = $false
if (Test-Path $StatusFile) {
    try {
        $Status = Get-Content $StatusFile -Raw | ConvertFrom-Json
        $Age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$Status.updated_epoch
        if ($Status.worker_id -and $Age -ge 0 -and $Age -le 5) {
            $WorkerAlreadyOnline = $true
            Write-Host "PLC worker is already online: $($Status.worker_id)" -ForegroundColor Green
        }
    } catch {
        $WorkerAlreadyOnline = $false
    }
}

$env:CRS_PLC_WORKER_ENABLED = "1"
$env:CRS_ALLOW_PLC_COMMUNICATION = "YES"
$env:CRS_PLC_WORKER_POLL_SECONDS = "0.25"
$env:CRS_FLASK_RELOAD = "0"

$WorkerProcess = $null
if (-not $WorkerAlreadyOnline) {
    $WorkerProcess = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList "scripts\run_plc_worker.py" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Minimized `
        -PassThru

    $WorkerReady = $false
    for ($Attempt = 0; $Attempt -lt 40; $Attempt++) {
        Start-Sleep -Milliseconds 250
        if (Test-Path $StatusFile) {
            try {
                $Status = Get-Content $StatusFile -Raw | ConvertFrom-Json
                $Age = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [double]$Status.updated_epoch
                if ($Status.worker_id -and $Age -ge 0 -and $Age -le 5) {
                    $WorkerReady = $true
                    break
                }
            } catch {
                # Worker may be replacing the heartbeat file atomically.
            }
        }
        if ($WorkerProcess.HasExited) {
            break
        }
    }

    if (-not $WorkerReady) {
        if ($WorkerProcess -and -not $WorkerProcess.HasExited) {
            Stop-Process -Id $WorkerProcess.Id -Force -ErrorAction SilentlyContinue
        }
        throw "PLC worker did not become ready within 10 seconds. Check the worker window for the exact error."
    }
    Write-Host "PLC worker ready in under 10 seconds." -ForegroundColor Green
}

$WebProcess = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList "app.py" `
    -WorkingDirectory $ProjectRoot `
    -PassThru

$ProcessInfo = [ordered]@{
    started_utc = [DateTime]::UtcNow.ToString("o")
    web_pid = $WebProcess.Id
    worker_pid = if ($WorkerProcess) { $WorkerProcess.Id } else { $null }
}
$ProcessInfo | ConvertTo-Json | Set-Content -Path $ProcessFile -Encoding UTF8

Write-Host ""
Write-Host "CRS started successfully." -ForegroundColor Green
Write-Host "Web URL : http://127.0.0.1:5000"
Write-Host "Web PID : $($WebProcess.Id)"
if ($WorkerProcess) {
    Write-Host "Worker PID: $($WorkerProcess.Id)"
}
Write-Host "Queued PLC operations should normally be claimed within 0.25 to 1 second."
Write-Host "Use Stop_CRS_Stack.bat to stop both processes." -ForegroundColor Cyan
