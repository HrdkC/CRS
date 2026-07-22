param(
    [string]$TaskName = "Apollo CRS Automatic Stack",
    [int]$StartupDelaySeconds = 30
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$AppPath = Join-Path $ProjectRoot "app.py"
$LogDir = Join-Path $ProjectRoot "logs"
$Runner = Join-Path $PSScriptRoot "run_crs_automatic.ps1"

if (-not (Test-Path $PythonExe)) {
    throw "CRS virtual environment not found: $PythonExe"
}
if (-not (Test-Path $AppPath)) {
    throw "CRS app.py not found: $AppPath"
}
if (-not (Test-Path $Runner)) {
    throw "CRS automatic runner not found: $Runner"
}

$CurrentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$Principal = New-Object Security.Principal.WindowsPrincipal($CurrentIdentity)
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run PowerShell as Administrator to install automatic CRS startup."
}

New-Item -ItemType Directory -Force $LogDir | Out-Null

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -AtStartup
$Trigger.Delay = "PT${StartupDelaySeconds}S"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

$TaskPrincipal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $TaskPrincipal `
    -Description "Runs CRS through Waitress and supervises the durable PLC worker automatically at Windows startup." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed and started scheduled task: $TaskName" -ForegroundColor Green
Write-Host "CRS will start automatically after every Windows restart." -ForegroundColor Green
Write-Host "Current automatic profile: Waitress + development security mode (HTTP)." -ForegroundColor Yellow
Write-Host "Production security mode must be enabled only after HTTPS, secure cookies, trusted hosts, and machine-level secrets are configured." -ForegroundColor Yellow
Write-Host "Web URL: http://127.0.0.1:5000"
