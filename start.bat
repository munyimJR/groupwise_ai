@echo off
rem GroupWise AI - one-click start (Windows).
rem Double-click this file: it starts the API (port 8000) and the web app (port 3000)
rem in two windows, then opens http://localhost:3000. Close those two windows to stop.
setlocal
cd /d "%~dp0"
title GroupWise AI launcher

rem ---- first run only: install what is missing
if not exist "backend\.venv\Scripts\python.exe" (
  echo [setup] Creating the Python environment for the API...
  python -m venv backend\.venv || goto :need_python
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto :failed
)
if not exist "frontend\node_modules" (
  echo [setup] Installing the web app packages...
  call npm --prefix frontend install || goto :need_node
)
if not exist "backend\.env" (
  echo [setup] backend\.env not found - copying the example ^(local SQLite database^).
  copy /y "backend\.env.example" "backend\.env" >nul
)

rem ---- warn if something is already running on the ports
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul && echo [note] Port 8000 is already in use - the API may already be running.
netstat -ano | findstr /r /c:":3000 .*LISTENING" >nul && echo [note] Port 3000 is already in use - the web app may already be running.

rem ---- start both servers in their own windows
start "GroupWise API - port 8000" /D "%CD%" cmd /k backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000
start "GroupWise Web - port 3000" /D "%CD%" cmd /k npm --prefix frontend run dev

rem ---- open the browser once the web app answers (up to ~3 minutes)
echo Starting GroupWise AI... the browser opens when it is ready.
powershell -NoProfile -Command "for($i=0;$i -lt 90;$i++){ try { Invoke-WebRequest 'http://localhost:3000' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Seconds 1 } }; exit 1"
if errorlevel 1 (
  echo The web app did not answer yet - check the two server windows, then open http://localhost:3000
) else (
  start "" http://localhost:3000
)
timeout /t 5 >nul
exit /b 0

:need_python
echo Python 3.11+ is required: https://www.python.org/downloads/  (tick "Add python.exe to PATH")
pause
exit /b 1
:need_node
echo Node.js 20+ is required: https://nodejs.org/
pause
exit /b 1
:failed
echo Installing the API packages failed - see the messages above.
pause
exit /b 1
