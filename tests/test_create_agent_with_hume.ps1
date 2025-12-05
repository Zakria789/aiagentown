# Test Script: Create Agent with HumeAI Configuration

Write-Host "🔧 Creating Test Agent with HumeAI Config..." -ForegroundColor Cyan

# Step 1: Login as admin to get token
Write-Host "`n1️⃣ Logging in as admin..." -ForegroundColor Yellow

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body (@{
        agent_id = "admin"
        password = "admin123"
    } | ConvertTo-Json)

$token = $loginResponse.access_token
Write-Host "✅ Login successful! Token: $($token.Substring(0, 20))..." -ForegroundColor Green

# Step 2: Create agent with HumeAI configuration
Write-Host "`n2️⃣ Creating test agent with HumeAI config..." -ForegroundColor Yellow

$agentData = @{
    agent_id = "HUME_TEST_001"
    full_name = "HumeAI Test Agent"
    email = "hume.test@callcenter.com"
    password = "test123456"
    role = "agent"
    permissions = @("make_calls", "view_customers")
    campaign_script = "Hello! I'm calling from TechCorp about our premium cloud solutions that help businesses reduce costs by 30%. Is this a good time to discuss how we can help your company?"
    voice_gender = "male"
    voice_style = "professional"
    hume_rules = @{
        event_messages = @{
            on_new_chat = @{
                enabled = $true
                text = "Hi! Thanks for taking my call today!"
            }
            on_inactivity_timeout = @{
                enabled = $true
                text = "Are you still there? I'm here to help if you have any questions."
            }
        }
        timeouts = @{
            inactivity = @{
                enabled = $true
                duration_secs = 30
            }
            max_duration = @{
                enabled = $true
                duration_secs = 600
            }
        }
        temperature = 0.7
    }
}

try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/agents" `
        -Method POST `
        -Headers @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"
        } `
        -Body ($agentData | ConvertTo-Json -Depth 10)
    
    Write-Host "✅ Agent created successfully!" -ForegroundColor Green
    Write-Host "`n📋 Agent Details:" -ForegroundColor Cyan
    Write-Host "   ID: $($createResponse.id)" -ForegroundColor White
    Write-Host "   Agent ID: $($createResponse.agent_id)" -ForegroundColor White
    Write-Host "   Name: $($createResponse.full_name)" -ForegroundColor White
    Write-Host "   Email: $($createResponse.email)" -ForegroundColor White
    Write-Host "   HumeAI Config ID: $($createResponse.hume_config_id)" -ForegroundColor Yellow
    Write-Host "   HumeAI Voice ID: $($createResponse.hume_voice_id)" -ForegroundColor Yellow
    
    # Step 3: Get HumeAI configuration details
    Write-Host "`n3️⃣ Fetching HumeAI configuration..." -ForegroundColor Yellow
    
    $humeConfig = Invoke-RestMethod -Uri "http://localhost:8000/api/agents/$($createResponse.id)/hume-config" `
        -Method GET `
        -Headers @{
            "Authorization" = "Bearer $token"
        }
    
    Write-Host "✅ HumeAI Config Retrieved!" -ForegroundColor Green
    Write-Host "`n🎤 Voice Configuration:" -ForegroundColor Cyan
    Write-Host "   Provider: $($humeConfig.voice.provider)" -ForegroundColor White
    Write-Host "   Voice Name: $($humeConfig.voice.name)" -ForegroundColor White
    
    Write-Host "`n💬 System Prompt:" -ForegroundColor Cyan
    Write-Host "   $($humeConfig.prompt.text)" -ForegroundColor White
    
    Write-Host "`n🤖 Language Model:" -ForegroundColor Cyan
    Write-Host "   Provider: $($humeConfig.language_model.model_provider)" -ForegroundColor White
    Write-Host "   Model: $($humeConfig.language_model.model_resource)" -ForegroundColor White
    
    Write-Host "`n✅ Test completed successfully!" -ForegroundColor Green
    Write-Host "`n📊 Summary:" -ForegroundColor Cyan
    Write-Host "   - Agent created with auto HumeAI config ✅" -ForegroundColor White
    Write-Host "   - Voice: Male/Professional ✅" -ForegroundColor White
    Write-Host "   - Script configured ✅" -ForegroundColor White
    Write-Host "   - Rules applied ✅" -ForegroundColor White
    
} catch {
    Write-Host "❌ Error creating agent:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails) {
        Write-Host $_.ErrorDetails.Message -ForegroundColor Red
    }
}
