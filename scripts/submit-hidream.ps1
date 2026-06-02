$wf = Get-Content 'C:\Users\qw\.openclaw\workspace\scripts\hidream_test.json' -Raw
$body = @{prompt=$wf} | ConvertTo-Json -Depth 10
$result = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/prompt' -Method Post -Body $body -ContentType 'application/json'
$result | ConvertTo-Json -Depth 5
