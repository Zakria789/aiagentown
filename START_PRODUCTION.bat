@echo off
echo ╔══════════════════════════════════════════════════════════╗
echo ║  CallTools + HumeAI Production System                   ║
echo ║  Automatic AI Voice Agent for Phone Calls               ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Starting production system...
echo.
echo ✅ System Features:
echo    - Automatic call detection
echo    - Real-time audio streaming
echo    - AI voice responses on phone
echo    - Call state management
echo.
pause

REM Start Backend Server
start "Backend Server (FastAPI)" cmd /k "cd /d E:\CallCenterAgent && venv\Scripts\activate && echo ✅ Starting Backend Server... && uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak

REM Start CallTools Monitor
start "CallTools Monitor" cmd /k "cd /d E:\CallCenterAgent && venv\Scripts\activate && echo ✅ Starting CallTools Monitor... && python calltools_call_event_monitor.py"

echo.
echo ✅ PRODUCTION SYSTEM STARTED!
echo.
echo Two windows opened:
echo   1. Backend Server (port 8000)
echo   2. CallTools Monitor (browser automation)
echo.
echo Wait for CallTools to login and set status to Available...
echo Then make or receive calls - AI will handle them automatically!
echo.
echo Press any key to exit this window (servers will keep running)
pause > nul
