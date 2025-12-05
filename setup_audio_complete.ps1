# Complete Installation & Testing Guide
# VB-Audio Virtual Cable + PyAudio + Audio Bridge

Write-Host @"
╔══════════════════════════════════════════════════════════╗
║  VB-Audio Virtual Cable Setup & Test                    ║
║  CallTools → HumeAI Audio Integration                   ║
╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Host ""
Write-Host "INSTALLATION CHECKLIST:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Step 1: VB-Audio Virtual Cable
Write-Host "[Step 1] VB-Audio Virtual Cable Installation" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "1. Download from: https://vb-audio.com/Cable/" -ForegroundColor White
Write-Host "2. Run VBCABLE_Setup_x64.exe as Administrator" -ForegroundColor White
Write-Host "3. Restart computer after installation" -ForegroundColor White
Write-Host ""
$vbInstalled = Read-Host "Have you installed VB-Cable? (y/n)"

if ($vbInstalled -eq 'y') {
    Write-Host "✓ VB-Cable marked as installed" -ForegroundColor Green
} else {
    Write-Host "⚠ Please install VB-Cable first!" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host ""
Write-Host "[Step 2] Windows Sound Settings Configuration" -ForegroundColor Cyan
Write-Host "─────────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "Opening Sound Settings..." -ForegroundColor White
Start-Process "ms-settings:sound"
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Configure the following:" -ForegroundColor Yellow
Write-Host "  Playback Tab:" -ForegroundColor White
Write-Host "    • Set 'CABLE Input' as DEFAULT playback device" -ForegroundColor White
Write-Host "    • Your browser audio will play through this" -ForegroundColor Gray
Write-Host ""
Write-Host "  Recording Tab:" -ForegroundColor White
Write-Host "    • Set 'CABLE Output' as DEFAULT recording device" -ForegroundColor White
Write-Host "    • This captures the audio for processing" -ForegroundColor Gray
Write-Host ""
$soundConfigured = Read-Host "Have you configured sound settings? (y/n)"

if ($soundConfigured -ne 'y') {
    Write-Host "⚠ Please configure sound settings before continuing" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host ""
Write-Host "[Step 3] PyAudio Installation" -ForegroundColor Cyan
Write-Host "───────────────────────────────────" -ForegroundColor Gray
Write-Host "Installing PyAudio..." -ForegroundColor White
.\install_pyaudio.ps1

Write-Host ""
Write-Host "[Step 4] Install Additional Dependencies" -ForegroundColor Cyan
Write-Host "────────────────────────────────────────────" -ForegroundColor Gray
pip install websockets

Write-Host ""
Write-Host "[Step 5] Test Audio Bridge" -ForegroundColor Cyan
Write-Host "─────────────────────────────" -ForegroundColor Gray
Write-Host "Starting server..." -ForegroundColor White
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\start_server.ps1"
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Testing audio bridge connection..." -ForegroundColor White
python -c @"
import asyncio
import websockets

async def test():
    uri = 'ws://localhost:8000/ws/audio/bridge'
    try:
        async with websockets.connect(uri) as ws:
            print('✓ Connected to audio bridge WebSocket!')
            await ws.send(b'\x00\x01\x02\x03')  # Test audio data
            print('✓ Sent test audio data')
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            print('✓ Received response from server')
            return True
    except Exception as e:
        print(f'× Connection failed: {e}')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"@

if ($?) {
    Write-Host "✓ Audio bridge test successful!" -ForegroundColor Green
} else {
    Write-Host "× Audio bridge test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host @"
╔══════════════════════════════════════════════════════════╗
║  Setup Complete!                                         ║
╚══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green

Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "─────────────────────────────────────────────" -ForegroundColor Gray
Write-Host "1. Start the audio bridge service:" -ForegroundColor White
Write-Host "   python audio_bridge_service.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Open CallTools in browser:" -ForegroundColor White
Write-Host "   https://east-1.calltools.io" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Login with credentials:" -ForegroundColor White
Write-Host "   Username: Al.Hassan" -ForegroundColor Cyan
Write-Host "   Password: Roofing123" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Make a test call - audio will route through:" -ForegroundColor White
Write-Host "   CallTools → VB-Cable → Backend → HumeAI → VB-Cable → CallTools" -ForegroundColor Gray
Write-Host ""

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
