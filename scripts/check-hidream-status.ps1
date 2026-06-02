param([string]$promptId)
$status = Invoke-RestMethod -Uri 'http://127.0.0.1:8188/history' -TimeoutSec 5
if ($status.$promptId) {
    $outputs = $status.$promptId.outputs
    Write-Output "DONE"
    $outputs | ConvertTo-Json -Depth 5
} else {
    Write-Output "PENDING"
}
