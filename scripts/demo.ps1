$ErrorActionPreference = "Stop"

$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://127.0.0.1:8000" }

Write-Host "Submitting declaration..."
$declaration = @{
  producer_id = "GREENPACK-001"
  month = "2026-04"
  declared_quantities_kg = @{
    rigid_plastic = 12000
    flexible_plastic = 8500
    multilayer_plastic = 3200
  }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Method Post -Uri "$baseUrl/submit" -ContentType "application/json" -Body $declaration |
  ConvertTo-Json -Depth 6

Write-Host "`n`nGetting reconciliation summary..."
Invoke-RestMethod -Method Get -Uri "$baseUrl/summary/GREENPACK-001/2026-04" |
  ConvertTo-Json -Depth 8

Write-Host "`n`nAsking policy question..."
$question = @{
  question = "What evidence should GreenPack keep for an audit?"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "$baseUrl/ask" -ContentType "application/json" -Body $question |
  ConvertTo-Json -Depth 6

Write-Host ""
