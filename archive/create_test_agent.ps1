$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"agent_id":"admin","password":"admin123"}'

$token = $login.access_token
Write-Host "Token received: $($token.Substring(0,30))..." -ForegroundColor Green

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
    "campaign_script": "Hello! I am calling from TechCorp about our premium cloud solutions.",
    "voice_gender": "male",
    "voice_style": "professional"
}
"@

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

Write-Host "`nCreating agent..." -ForegroundColor Cyan

$agent = Invoke-RestMethod -Uri "http://localhost:8000/api/agents/" -Method POST -Headers $headers -Body $agentBody

Write-Host "`nAgent Created Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "ID: $($agent.id)"
Write-Host "Agent ID: $($agent.agent_id)"
Write-Host "Name: $($agent.full_name)"
Write-Host "Email: $($agent.email)"
Write-Host "HumeAI Config ID: $($agent.hume_config_id)" -ForegroundColor Yellow
Write-Host "HumeAI Voice ID: $($agent.hume_voice_id)" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Cyan
