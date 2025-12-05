# Clean up unnecessary development/test files for production deployment

Write-Host "🧹 Cleaning up development files..." -ForegroundColor Yellow

# Remove all .md files except production docs
$keepDocs = @("PRODUCTION_README.md", "README.md")
Get-ChildItem -Path "." -Filter "*.md" | Where-Object { $keepDocs -notcontains $_.Name } | Remove-Item -Force
Write-Host "✅ Removed documentation files" -ForegroundColor Green

# Remove all test files
Get-ChildItem -Path "." -Filter "test*.py" | Remove-Item -Force
Get-ChildItem -Path "." -Filter "test*.ps1" | Remove-Item -Force
Get-ChildItem -Path "." -Filter "check_*.py" | Remove-Item -Force
Get-ChildItem -Path "." -Filter "*_test.py" | Remove-Item -Force
Write-Host "✅ Removed test files" -ForegroundColor Green

# Remove debug/development scripts
$devScripts = @(
    "create_test_agent.ps1",
    "decode_token.py",
    "find_*.py",
    "get_*.py",
    "list_*.py",
    "update_*.py",
    "delete_*.py",
    "verify_*.py",
    "debug_*.py",
    "quick_*.py",
    "make_call_*.py",
    "call_now_*.py",
    "direct_service_test.py",
    "simple_hume_bridge.py",
    "vb_cable_hume_bridge.py",
    "audio_bridge_service.py",
    "complete_voice_dialer.py",
    "auto_dialer_complete.py",
    "calltools_complete_flow.py",
    "create_hume_agent_complete.py",
    "create_new_hume_agent.py",
    "final_*.py",
    "integrated_hume_dialer.py",
    "manual_calltools_guide.py",
    "setup_tmdialer.py"
)

foreach ($pattern in $devScripts) {
    Get-ChildItem -Path "." -Filter $pattern -ErrorAction SilentlyContinue | Remove-Item -Force
}
Write-Host "✅ Removed development scripts" -ForegroundColor Green

# Remove all PNG screenshot files
Get-ChildItem -Path "." -Filter "*.png" | Remove-Item -Force
Write-Host "✅ Removed screenshot files" -ForegroundColor Green

# Remove unused batch files
$keepBatch = @("START_PRODUCTION.ps1")
Get-ChildItem -Path "." -Filter "*.bat" | Remove-Item -Force
Get-ChildItem -Path "." -Filter "start_*.ps1" | Where-Object { $_.Name -ne "START_PRODUCTION.ps1" } | Remove-Item -Force
Write-Host "✅ Removed old batch files" -ForegroundColor Green

# Remove chrome extension (not needed for automation)
if (Test-Path "chrome_extension") {
    Remove-Item -Path "chrome_extension" -Recurse -Force
    Write-Host "✅ Removed Chrome extension" -ForegroundColor Green
}

# Remove extra setup scripts
$removeSetup = @("setup_audio_complete.ps1", "install_pyaudio.ps1")
foreach ($file in $removeSetup) {
    if (Test-Path $file) {
        Remove-Item -Path $file -Force
    }
}
Write-Host "✅ Removed extra setup scripts" -ForegroundColor Green

# Keep only essential files
Write-Host ""
Write-Host "📦 Production files retained:" -ForegroundColor Cyan
Write-Host "   - app/ (FastAPI backend)" -ForegroundColor White
Write-Host "   - calltools_webrtc_bridge.py (WebRTC bridge)" -ForegroundColor White
Write-Host "   - calltools_audio_bridge.py (VB-Cable fallback)" -ForegroundColor White
Write-Host "   - setup_database.py (Initial setup)" -ForegroundColor White
Write-Host "   - create_admin.py (Create admin user)" -ForegroundColor White
Write-Host "   - requirements.txt (Dependencies)" -ForegroundColor White
Write-Host "   - .env (Configuration)" -ForegroundColor White
Write-Host "   - PRODUCTION_README.md (Documentation)" -ForegroundColor White
Write-Host "   - START_PRODUCTION.ps1 (Startup script)" -ForegroundColor White
Write-Host ""
Write-Host "✅ Cleanup complete! Ready for production deployment." -ForegroundColor Green
