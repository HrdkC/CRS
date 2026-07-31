@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo CRS virtual-environment Python was not found:
    echo %PYTHON%
    echo.
    echo Run Setup_CRS_New_Workstation.bat before creating a support ZIP.
    pause
    exit /b 1
)

echo Creating a consistent CRS support ZIP...
echo The running CRS application does not need to be stopped.
echo.

"%PYTHON%" "%CD%\scripts\create_crs_support_zip.py"
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Support ZIP creation failed. No incomplete ZIP should be shared.
) else (
    echo Support ZIP creation completed.
    echo The ZIP is available in the parent folder beside this project.
)

pause
exit /b %RESULT%
