@echo off
REM =====================================================================
REM Kalibr Publisher - one-click local launcher (no Docker).
REM Starts API (:8000) + Web (:3000) in the background, then opens
REM the web UI. No console windows stay open.
REM
REM Requirements (already set up):
REM   - apps/api/.venv        (Python venv with deps)
REM   - apps/web/.next/standalone/server.js  (production web build)
REM
REM To stop:  run stop.bat   (or double-click it)
REM =====================================================================
SETLOCAL
SET "REPO=C:\Users\user\Desktop\kalibr-publisher"
SET "LAUNCHER=C:\Users\user\Desktop\AI\run_kalibr.py"
SET "PYTHON=C:\Users\user\Desktop\kalibr-publisher\apps\api\.venv\Scripts\python.exe"

echo ====================================================================
echo  Kalibr Publisher - starting (API + Web, background)...
echo ====================================================================

IF NOT EXIST "%PYTHON%" (
    echo [ERROR] API venv not found: %PYTHON%
    echo         Run 'uv sync' in apps/api first.
    pause
    exit /b 1
)

IF NOT EXIST "%LAUNCHER%" (
    echo [ERROR] Launcher not found: %LAUNCHER%
    pause
    exit /b 1
)

REM Launch via the proven background launcher (no windows left open).
"%PYTHON%" "%LAUNCHER%"
IF ERRORLEVEL 1 (
    echo [ERROR] Launcher reported a problem (already running? check .kalibr_pids).
    pause
    exit /b 1
)

echo.
echo  Waiting for servers to come up...
timeout /t 4 /nobreak >nul

REM Open the web UI in the default browser.
start "" "http://localhost:3000/uz/system"

echo.
echo  Done. Open the browser if it did not open automatically:
echo    Web UI : http://localhost:3000  (/uz , /ru)
echo    System : http://localhost:3000/uz/system
echo    API docs: http://127.0.0.1:8000/docs
echo.
echo  To stop, run stop.bat (or double-click it).
echo ====================================================================
timeout /t 3 /nobreak >nul
