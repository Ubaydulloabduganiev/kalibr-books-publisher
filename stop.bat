@echo off
REM =====================================================================
REM Kalibr Publisher - stop the background API + Web services.
REM (Companion to run.bat)
REM =====================================================================
SETLOCAL
SET "LAUNCHER=C:\Users\user\Desktop\AI\stop_kalibr.py"
SET "PYTHON=C:\Users\user\Desktop\kalibr-publisher\apps\api\.venv\Scripts\python.exe"

echo Stopping Kalibr Publisher...
IF EXIST "%LAUNCHER%" (
    "%PYTHON%" "%LAUNCHER%"
) ELSE (
    REM fallback: kill by port / process
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /PID %%a /T /F >nul 2>&1
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do taskkill /PID %%a /T /F >nul 2>&1
)
echo Stopped.
timeout /t 2 /nobreak >nul
