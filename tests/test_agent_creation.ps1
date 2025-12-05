# Wait for server to be ready
Write-Host "Waiting for server to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Login
Write-Host "`n1. Logging in as admin..." -ForegroundColor Cyan
try {
    $login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"agent_id":"admin","password":"admin123"}'
    $token = $login.access_token
    Write-Host "   ✅ Login successful" -ForegroundColor Green
    Write-Host "   Token: $($token.Substring(0,30))..." -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Login failed: $_" -ForegroundColor Red
    exit 1
}

# Create agent
Write-Host "`n2. Creating new agent with HumeAI config..." -ForegroundColor Cyan

$agentBody = @"
{
    "agent_id": "HUME001",
    "full_name": "HumeAI Test Agent",
    "email": "hume001@test.com",
    "password": "Test@123",
    "role": "agent",
    "permissions": ["make_calls"],
    "phone": "+1234567890",
    "dialer_extension": "101",
    "campaign_script": "Hello! I am calling from TechCorp about our premium cloud solutions. How are you today?",
    "voice_gender": "male",
    "voice_style": "professional"
}
"@

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $agent = Invoke-RestMethod -Uri "http://localhost:8000/api/agents/" -Method POST -Headers $headers -Body $agentBody
    
    Write-Host "   ✅ Agent created successfully!" -ForegroundColor Green
    Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║  Agent Details                             ║" -ForegroundColor Cyan
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║  ID: $($agent.id.ToString().PadRight(40))║"
    Write-Host "║  Agent ID: $($agent.agent_id.PadRight(34))║"
    Write-Host "║  Name: $($agent.full_name.PadRight(37))║"
    Write-Host "║  Email: $($agent.email.PadRight(36))║"
    Write-Host "║  Role: $($agent.role.PadRight(37))║"
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║  HumeAI Configuration                      ║" -ForegroundColor Yellow
    Write-Host "╠════════════════════════════════════════════╣" -ForegroundColor Cyan
    
    if ($agent.hume_config_id) {
        Write-Host "║  Config ID: $($agent.hume_config_id.Substring(0,27).PadRight(30))║" -ForegroundColor Green
        Write-Host "║  Voice ID: $($agent.hume_voice_id.Substring(0,28).PadRight(31))║" -ForegroundColor Green
    } else {
        Write-Host "║  ❌ HumeAI config not created             ║" -ForegroundColor Red
    }
    
    Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
    
} catch {
    Write-Host "   ❌ Agent creation failed!" -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
    Write-Host "   Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Test completed successfully!" -ForegroundColor Green
