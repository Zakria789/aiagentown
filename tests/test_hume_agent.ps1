$ErrorActionPreference = "Stop"

Write-Host "Creating test agent with HumeAI..." -ForegroundColor Cyan

# Login
$loginBody = '{"agent_id":"admin","password":"admin123"}'
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody

Write-Host "Logged in successfully" -ForegroundColor Green

# Create agent
$agentJson = @"
{
    "agent_id": "HUME001",
    "full_name": "HumeAI Test Agent",
    "email": "hume@test.com",
    "password": "test123",
    "role": "agent",
    "permissions": ["make_calls"],
    "campaign_script": "Hello! I am calling from TechCorp about our services.",
    "voice_gender": "male",
    "voice_style": "professional"
}
"@

$headers = @{
    "Authorization" = "Bearer $($login.access_token)"
    "Content-Type" = "application/json"
}

$agent = Invoke-RestMethod -Uri "http://localhost:8000/api/agents" -Method POST -Headers $headers -Body $agentJson

Write-Host "Agent created!" -ForegroundColor Green
Write-Host "ID: $($agent.id)"
Write-Host "Agent ID: $($agent.agent_id)"
Write-Host "HumeAI Config ID: $($agent.hume_config_id)" -ForegroundColor Yellow
Write-Host "HumeAI Voice ID: $($agent.hume_voice_id)" -ForegroundColor Yellow
