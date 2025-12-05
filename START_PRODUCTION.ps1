#!/usr/bin/env pwsh
<#
.SYNOPSIS
    FastAPI Call Center - Production Startup
.DESCRIPTION
    Starts FastAPI server with complete logging and WebRTC support
#>

Write-Host "=" -NoNewline
for ($i=0; $i -lt 69; $i++) { 
    Write-Host "=" -NoNewline 
}
Write-Host ""
Write-Host "🚀 FastAPI Call Center System - PRODUCTION MODE" -ForegroundColor Green
Write-Host "=" -NoNewline
for ($i=0; $i -lt 69; $i++) { 
    Write-Host "=" -NoNewline 
}
Write-Host ""
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "   Installing dependencies..." -ForegroundColor Yellow
    & venv\Scripts\Activate.ps1
    pip install -r requirements.txt
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& venv\Scripts\Activate.ps1

# Create logs directory
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "✅ Created logs directory" -ForegroundColor Green
}

# Check database
if (-not (Test-Path "callcenter.db")) {
    Write-Host "📊 Database not found - initializing..." -ForegroundColor Cyan
    python setup_database.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database initialized successfully" -ForegroundColor Green
        Write-Host ""
        Write-Host "📝 Creating admin user..." -ForegroundColor Cyan
        python create_admin.py
    } else {
        Write-Host "❌ Database initialization failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=" -NoNewline; for ($i=0; $i -lt 69; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host "📋 System Configuration:" -ForegroundColor Cyan
Write-Host "   • FastAPI Server: http://0.0.0.0:8000" -ForegroundColor White
Write-Host "   • API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   • WebSocket (WebRTC): ws://localhost:8000/ws/webrtc-audio" -ForegroundColor White
Write-Host "   • CallTools URL: https://east-1.calltools.io" -ForegroundColor White
Write-Host "   • HumeAI: Configured (Config ID: 64cfa125...)" -ForegroundColor White
Write-Host "   • Database: SQLite (callcenter.db)" -ForegroundColor White
Write-Host "   • Logs: logs/production.log" -ForegroundColor White
Write-Host "=" -NoNewline; for ($i=0; $i -lt 69; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host ""
Write-Host "🎯 Quick Start Guide:" -ForegroundColor Yellow
Write-Host "   1. Go to: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   2. Create agent: POST /api/agents/" -ForegroundColor White
Write-Host "   3. Start monitoring: POST /api/agents/(id)/start" -ForegroundColor White
Write-Host "   4. Call 2015024650 from mobile phone" -ForegroundColor White
Write-Host "   5. Check logs: Get-Content logs/production.log -Tail 50 -Wait" -ForegroundColor White
Write-Host ""
Write-Host "=" -NoNewline; for ($i=0; $i -lt 69; $i++) { Write-Host "=" -NoNewline }
Write-Host ""
Write-Host ""
Write-Host "🚀 Starting FastAPI server with detailed logging..." -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start server with enhanced logging
try {
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info --access-log
} catch {
    Write-Host ""
    Write-Host "❌ Server stopped" -ForegroundColor Red
    exit 1
}
