$token = Get-Content "$env:USERPROFILE\.openclaw\gateway.token"
$headers = @{ 'Authorization' = "Bearer $token" }
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:18789/health' -Headers $headers -TimeoutSec 3 -UseBasicParsing
    Write-Host "Gateway: OK"
    Write-Host "Status:" $r.StatusCode
} catch {
    Write-Host "Gateway: DOWN"
    Write-Host "Error:" $_.Exception.Message
}
