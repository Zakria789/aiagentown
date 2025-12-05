# Test HumeAI Integration
Write-Host "Testing HumeAI Integration..." -ForegroundColor Cyan
Write-Host ""

# Login
Write-Host "Step 1: Login" -ForegroundColor Yellow
$loginBody = '{"agent_id":"admin","password":"admin123"}'
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
Write-Host "Login successful!" -ForegroundColor Green
Write-Host "Token: $($login.access_token.Substring(0,30))..." -ForegroundColor Gray
Write-Host ""

# Create agent
Write-Host "Step 2: Create Agent with HumeAI" -ForegroundColor Yellow

$agentBody = @"
{
    "agent_id": "HUME002",
    "full_name": "HumeAI Test Agent 2",
    "email": "hume002@test.com",
    "password": "Test@123",
    "phone": "+1234567890",
    "role": "agent",
    "permissions": ["make_calls"],
    "dialer_extension": "102",
    "campaign_script": "Hello! I am calling from TechCorp about our premium cloud solutions."
}
"@

$headers = @{
    "Authorization" = "Bearer $($login.access_token)"
    "Content-Type" = "application/json"
}

try {
    $agent = Invoke-RestMethod -Uri "http://localhost:8000/api/agents/" -Method POST -Headers $headers -Body $agentBody
    
    Write-Host "SUCCESS! Agent created" -ForegroundColor Green
    Write-Host ""
    Write-Host "ID: $($agent.id)"
    Write-Host "Agent ID: $($agent.agent_id)"
    Write-Host "Name: $($agent.full_name)"
    Write-Host "Email: $($agent.email)"
    Write-Host ""
    
    if ($agent.hume_config_id) {
        Write-Host "HumeAI Config ID: $($agent.hume_config_id)" -ForegroundColor Yellow
        Write-Host "HumeAI Voice ID: $($agent.hume_voice_id)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "HumeAI configuration created automatically!" -ForegroundColor Green
    } else {
        Write-Host "WARNING: HumeAI config not created" -ForegroundColor Red
    }
    
} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    } else {
        Write-Host $_.Exception.Message -ForegroundColor Red
    }
}
