$token = Get-Content 'C:\Users\qw\.openclaw\gateway.token'
$headers = @{
    'Authorization' = 'Bearer ' + $token
    'Content-Type' = 'application/json'
}
$body = @{
    method = 'conversations.list'
    params = @{}
} | ConvertTo-Json -Depth 5

try {
    $r = Invoke-RestMethod -Uri 'http://127.0.0.1:18789/rpc' -Method Post -Headers $headers -Body $body -TimeoutSec 8
    $r | ConvertTo-Json -Depth 10
} catch {
    $_.Exception.Message
}
