@echo off
setlocal
cd /d "%~dp0"
set HOST=127.0.0.1
set PORT=47834

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating Python virtual environment...
  python -m venv .venv || goto :error
)

.venv\Scripts\python.exe -c "import fastapi, uvicorn, pydantic" >nul 2>nul
if errorlevel 1 (
  echo [setup] Installing backend dependencies...
  .venv\Scripts\python.exe -m pip install -e ".[web]" || goto :error
)

if not exist "web\frontend\dist\index.html" (
  echo [setup] Building frontend assets...
  pushd web\frontend
  npm install || (popd & goto :error)
  npm run build || (popd & goto :error)
  popd
)

echo [run] Antigravity Session Patcher Web UI
echo [run] http://%HOST%:%PORT%
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://%HOST%:%PORT%/"
.venv\Scripts\python.exe -m codex_session_patcher.cli --web --host %HOST% --port %PORT%
goto :eof

:error
echo.
echo [error] Failed to start Antigravity Session Patcher.
pause
exit /b 1
