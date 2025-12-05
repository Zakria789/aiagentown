# Wait for server and test agent creation

Write-Host "Waiting for server to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Login
Write-Host ""
Write-Host "1. Logging in..." -ForegroundColor Cyan
try {
    $login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"agent_id":"admin","password":"admin123"}'
    $token = $login.access_token
    Write-Host "Login successful" -ForegroundColor Green
    Write-Host "   Token: $($token.Substring(0,40))..." -ForegroundColor Gray
} catch {
    Write-Host "Login failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Create agent
Write-Host ""
Write-Host "2. Creating agent with HumeAI config..." -ForegroundColor Cyan

$agentData = @{
    agent_id = "HUME001"
    full_name = "HumeAI Test Agent"
    email = "hume001@test.com"
    password = "Test@123"
    phone = "+1234567890"
    role = "agent"
    permissions = @("make_calls")
    dialer_extension = "101"
    campaign_script = "Hello! I am calling from TechCorp about our premium cloud solutions. How can I assist you today?"
    voice_gender = "male"
    voice_style = "professional"
} | ConvertTo-Json

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

try {
    $agent = Invoke-RestMethod -Uri "http://localhost:8000/api/agents/" -Method POST -Headers $headers -Body $agentData
    
    Write-Host "Agent created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "║             AGENT DETAILS                          ║" -ForegroundColor Cyan
    Write-Host "╠════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║ ID:                $($agent.id.ToString().PadRight(33))║" -ForegroundColor White
    Write-Host "║ Agent ID:          $($agent.agent_id.PadRight(33))║" -ForegroundColor White
    Write-Host "║ Name:              $($agent.full_name.PadRight(33))║" -ForegroundColor White
    Write-Host "║ Email:             $($agent.email.PadRight(33))║" -ForegroundColor White
    Write-Host "║ Role:              $($agent.role.PadRight(33))║" -ForegroundColor White
    Write-Host "╠════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║             HUMEAI CONFIGURATION                   ║" -ForegroundColor Cyan
    Write-Host "HUMEAI CONFIGURATION" -ForegroundColor Cyan
    
    if ($agent.hume_config_id) {
        Write-Host "Config ID: $($agent.hume_config_id)" -ForegroundColor Yellow
        Write-Host "Voice ID: $($agent.hume_voice_id)" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "SUCCESS: HumeAI configuration created automatically!" -ForegroundColor Green
    } else {
        Write-Host "Config ID: NOT CREATED" -ForegroundColor Red
        Write-Host ""
        Write-Host "WARNING: HumeAI configuration was not created" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Agent creation failed!" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        try {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "Error: $($errorDetails.detail)" -ForegroundColor Red
        } catch {
            Write-Host "Error: $($_.ErrorDetails.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    exit 1
}
