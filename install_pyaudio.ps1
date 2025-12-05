# PyAudio Installation for Windows
# Required for VB-Audio Virtual Cable integration

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PyAudio Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "[1/4] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "✓ $pythonVersion" -ForegroundColor Green
Write-Host ""

# Step 2: Try pip install first
Write-Host "[2/4] Attempting pip install pyaudio..." -ForegroundColor Yellow
try {
    pip install pyaudio 2>&1
    $pipSuccess = $?
} catch {
    $pipSuccess = $false
}

if ($pipSuccess) {
    Write-Host "✓ PyAudio installed successfully!" -ForegroundColor Green
} else {
    Write-Host "× Pip install failed (expected on Windows)" -ForegroundColor Red
    Write-Host ""
    
    # Step 3: Download precompiled wheel
    Write-Host "[3/4] Downloading precompiled PyAudio wheel..." -ForegroundColor Yellow
    Write-Host "Please visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Download the appropriate .whl file for your Python version:" -ForegroundColor Yellow
    Write-Host "  - PyAudio-0.2.11-cp312-cp312-win_amd64.whl (Python 3.12, 64-bit)" -ForegroundColor White
    Write-Host "  - PyAudio-0.2.11-cp311-cp311-win_amd64.whl (Python 3.11, 64-bit)" -ForegroundColor White
    Write-Host "  - PyAudio-0.2.11-cp310-cp310-win_amd64.whl (Python 3.10, 64-bit)" -ForegroundColor White
    Write-Host ""
    
    # Wait for user to download
    $wheelPath = Read-Host "Enter the full path to the downloaded .whl file (or press Enter to skip)"
    
    if ($wheelPath -and (Test-Path $wheelPath)) {
        Write-Host ""
        Write-Host "[4/4] Installing PyAudio from wheel..." -ForegroundColor Yellow
        pip install $wheelPath
        
        if ($?) {
            Write-Host "✓ PyAudio installed successfully from wheel!" -ForegroundColor Green
        } else {
            Write-Host "× Failed to install from wheel" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "Manual Installation Steps:" -ForegroundColor Yellow
        Write-Host "1. Download .whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio" -ForegroundColor White
        Write-Host "2. Run: pip install path\to\PyAudio-0.2.11-cpXXX-cpXXX-win_amd64.whl" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test PyAudio
Write-Host "Testing PyAudio import..." -ForegroundColor Yellow
python -c "import pyaudio; print('✓ PyAudio imported successfully!')" 2>&1

if ($?) {
    Write-Host ""
    Write-Host "✓ All good! PyAudio is ready to use." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "× PyAudio import failed. Please install manually." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
