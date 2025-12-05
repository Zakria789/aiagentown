@echo off
echo ========================================
echo COMPLETE SYSTEM TEST
echo ========================================
echo.
echo Step 1: Checking backend...
curl http://localhost:8000/health 2>nul
if %errorlevel% neq 0 (
    echo Backend NOT running!
    echo.
    echo Starting backend in new window...
    start "CallCenter Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && uvicorn app.main:app --reload"
    timeout /t 5 /nobreak >nul
    echo.
)

echo Step 2: Starting browser test...
call venv\Scripts\activate
python test_automated.py

echo.
echo Test completed!
pause
