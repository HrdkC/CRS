@echo off
setlocal
cd /d "%~dp0"

set "CRS_VENV=.venv"
if exist "venv\Scripts\python.exe" set "CRS_VENV=venv"

if not exist "%CRS_VENV%\Scripts\python.exe" (
    echo [1/6] Creating CRS virtual environment...
    py -3 -m venv "%CRS_VENV%"
    if errorlevel 1 exit /b 1
) else (
    echo [1/6] CRS virtual environment already exists.
)

echo [2/6] Installing verified Python dependencies...
"%CRS_VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/6] Creating the machine-local CRS session secret...
"%CRS_VENV%\Scripts\python.exe" scripts\configure_secret_key.py
if errorlevel 1 exit /b 1

echo [4/6] Building the production UI assets...
"%CRS_VENV%\Scripts\python.exe" scripts\build_css_bundle.py
if errorlevel 1 exit /b 1

echo [5/6] Creating or upgrading the generic CRS database...
"%CRS_VENV%\Scripts\python.exe" scripts\bootstrap_crs_system.py --no-seed-users --strict
if errorlevel 1 (
    echo CRS database bootstrap failed. Review reports\bootstrap.
    exit /b 1
)

echo [6/6] Validating CRS startup...
"%CRS_VENV%\Scripts\python.exe" scripts\run_crs.py --check
if errorlevel 1 exit /b 1

echo.
echo CRS setup completed. Start the service with run_crs.bat.
exit /b 0
