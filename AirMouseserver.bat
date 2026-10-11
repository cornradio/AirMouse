@echo off
cd /d "%~dp0"

set "DEPS_FLAG=deps_ok.txt"

if exist "%DEPS_FLAG%" (
    echo dependencies already verified, skipping package check.
) else (
    echo checking python dependencies...
    pip install -r requirments.txt
    if errorlevel 1 (
        echo dependency check failed.
        pause
        exit /b 1
    )
    > "%DEPS_FLAG%" echo deps verified
    echo dependencies verified. marker written to %DEPS_FLAG%.
)

where pythonw >nul 2>nul
if errorlevel 1 (
    start "" python server.py
) else (
    start "" pythonw server.py
)
