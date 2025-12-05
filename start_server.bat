@echo off
REM Windows Batch Script to Start FastAPI Server

echo ========================================
echo   FastAPI Call Center - Starting...
echo ========================================

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Start server
echo Starting FastAPI server...
echo.
echo Server will be available at:
echo   - http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
