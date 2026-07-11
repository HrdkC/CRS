@echo off
setlocal
cd /d "%~dp0"

set "CRS_PYTHON="
if exist ".venv\Scripts\python.exe" set "CRS_PYTHON=.venv\Scripts\python.exe"
if not defined CRS_PYTHON if exist "venv\Scripts\python.exe" set "CRS_PYTHON=venv\Scripts\python.exe"

if not defined CRS_PYTHON (
    echo CRS virtual environment was not found.
    echo Run setup_crs.bat first.
    exit /b 1
)

"%CRS_PYTHON%" scripts\run_crs.py %*
exit /b %errorlevel%
