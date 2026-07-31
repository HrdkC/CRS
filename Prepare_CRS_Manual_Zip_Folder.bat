@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=%CD%\venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo CRS virtual-environment Python was not found:
    echo %PYTHON%
    echo.
    echo Run Setup_CRS_New_Workstation.bat before preparing the folder.
    pause
    exit /b 1
)

echo Preparing an unlocked CRS folder for manual Windows ZIP creation...
echo The running CRS application does not need to be stopped.
echo.

"%PYTHON%" "%CD%\scripts\create_crs_support_zip.py" --folder-only
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Manual ZIP folder preparation failed.
) else (
    echo Preparation completed.
    echo Open the new CRS_Manual_Zip_Ready folder on the Desktop.
    echo Right-click that folder and select Compress to ZIP.
)

pause
exit /b %RESULT%
