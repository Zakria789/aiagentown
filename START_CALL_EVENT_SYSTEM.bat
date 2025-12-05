@echo off
echo ╔══════════════════════════════════════════════════════════╗
echo ║  CallTools + HumeAI Call Event System                   ║
echo ║  Automatic call detection and AI agent activation       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Starting in 2 terminals:
echo   1. FastAPI Backend (port 8000)
echo   2. CallTools Call Event Monitor
echo.
pause

REM Start FastAPI Backend
start "FastAPI Backend" cmd /k "cd /d E:\CallCenterAgent && venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
timeout /t 5 /nobreak

REM Start CallTools Monitor
start "CallTools Monitor" cmd /k "cd /d E:\CallCenterAgent && venv\Scripts\activate && python calltools_call_event_monitor.py"

echo.
echo ✅ System started!
echo.
echo Backend running at: http://localhost:8000
echo Monitor running in separate window
echo.
echo Wait for incoming call - HumeAI will activate automatically!
echo.
pause
