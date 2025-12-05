@echo off
echo ╔══════════════════════════════════════════════════════════╗
echo ║  CallTools + HumeAI Audio Bridge                         ║
echo ║  Quick Start                                             ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

echo [Step 1/3] Starting FastAPI Backend...
start "FastAPI Server" cmd /k "venv\Scripts\activate & uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [Step 2/3] Waiting for server to start...
timeout /t 5 /nobreak >nul

echo [Step 3/3] Starting CallTools Audio Bridge...
call venv\Scripts\activate
python calltools_audio_bridge.py

pause
