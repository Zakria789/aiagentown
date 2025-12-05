$login = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"agent_id":"admin","password":"admin123"}'

Write-Host "Full login response:" -ForegroundColor Cyan
$login | ConvertTo-Json -Depth 10
Write-Host "`nToken:" -ForegroundColor Yellow
Write-Host $login.access_token
Write-Host "`nToken type:" -ForegroundColor Yellow  
Write-Host $login.token_type
