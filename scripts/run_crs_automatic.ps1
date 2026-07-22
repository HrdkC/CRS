$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$LogDir = Join-Path $ProjectRoot "logs"
$StdoutLog = Join-Path $LogDir "crs_stack_stdout.log"
$StderrLog = Join-Path $LogDir "crs_stack_stderr.log"
$StartupLog = Join-Path $LogDir "crs_autostart.log"

New-Item -ItemType Directory -Force $LogDir | Out-Null
Set-Location $ProjectRoot

function Write-StartupLog([string]$Message) {
    $Line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $StartupLog -Value $Line -Encoding UTF8
}

if (-not (Test-Path $PythonExe)) {
    Write-StartupLog "ERROR: Virtual environment Python not found: $PythonExe"
    exit 2
}

# HTTP server selection and security mode are intentionally separate.
# Until HTTPS/trusted-host commissioning is complete, automatic startup uses
# the existing development security profile but runs through Waitress.
$env:CRS_DEPLOYMENT_MODE = if ($env:CRS_DEPLOYMENT_MODE) {
    $env:CRS_DEPLOYMENT_MODE
} else {
    "development"
}
$env:CRS_USE_WAITRESS = if ($env:CRS_USE_WAITRESS) {
    $env:CRS_USE_WAITRESS
} else {
    "1"
}
$env:CRS_AUTO_START_PLC_WORKER = "1"
$env:CRS_FLASK_RELOAD = "0"
$env:CRS_FLASK_DEBUG = "0"
$env:PYTHONUNBUFFERED = "1"

Write-StartupLog (
    "Starting CRS; security_mode={0}; waitress={1}; user={2}" -f `
    $env:CRS_DEPLOYMENT_MODE, $env:CRS_USE_WAITRESS, `
    [Security.Principal.WindowsIdentity]::GetCurrent().Name
)

try {
    & $PythonExe "app.py" 1>> $StdoutLog 2>> $StderrLog
    $ExitCode = $LASTEXITCODE
    Write-StartupLog "CRS stopped; exit_code=$ExitCode"
    exit $ExitCode
}
catch {
    Write-StartupLog "ERROR: $($_.Exception.Message)"
    $_ | Out-String | Add-Content -Path $StderrLog -Encoding UTF8
    exit 1
}
