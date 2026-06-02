$dir = "G:\AI\models\SANA-WM_bidirectional"
$totalSize = (Get-ChildItem $dir -Recurse -File | Where-Object { $_.Name -notmatch '\.(log|tmp|lock)$' -and $_.Name -ne 'CACHEDIR.TAG' -and $_.Name -ne '.gitattributes' -and $_.Name -ne '.gitignore' } | Measure-Object -Property Length -Sum).Sum
$fileCount = (Get-ChildItem $dir -Recurse -File | Where-Object { $_.Name -notmatch '\.(log|tmp|lock)$' -and $_.Name -ne 'CACHEDIR.TAG' -and $_.Name -ne '.gitattributes' -and $_.Name -ne '.gitignore' }).Count
Write-Host "=== SANA-WM_bidirectional ==="
Write-Host "Files: $fileCount"
Write-Host "Total size: $([math]::Round($totalSize/1GB, 2)) GB"

$shards = Get-ChildItem "$dir\refiner\text_encoder" -Filter "model-*-of-00011.safetensors" -EA SilentlyContinue
Write-Host "text_encoder shards: $($shards.Count)/11"

$ditSize = (Get-ChildItem "$dir\dit" -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$vaeSize = (Get-ChildItem "$dir\vae" -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$transformerSize = (Get-ChildItem "$dir\refiner\transformer" -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$connectorsSize = (Get-ChildItem "$dir\refiner\connectors" -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$teSize = (Get-ChildItem "$dir\refiner\text_encoder" -File -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum

Write-Host ""
Write-Host "--- Components ---"
Write-Host "dit: $([math]::Round($ditSize/1GB,2)) GB"
Write-Host "refiner/text_encoder: $([math]::Round($teSize/1GB,2)) GB ($($shards.Count)/11 shards)"
Write-Host "refiner/transformer: $([math]::Round($transformerSize/1GB,2)) GB"
Write-Host "refiner/connectors: $([math]::Round($connectorsSize/1MB,2)) MB"
Write-Host "vae: $([math]::Round($vaeSize/1MB,2)) MB"

# Check for incomplete downloads
Write-Host ""
Write-Host "--- Incomplete downloads ---"
$incomplete = Get-ChildItem $dir -Recurse -File | Where-Object { $_.Name -match '\.tmp$|\.partial$|\.downloading$' }
if ($incomplete.Count -eq 0) {
    Write-Host "None found - all downloads look complete!"
} else {
    $incomplete | ForEach-Object { Write-Host "  $($_.FullName) ($([math]::Round($_.Length/1MB,2)) MB)" }
}

# Also check .cache for any pending chunks
$cacheDir = "$dir\.cache\huggingface\download"
if (Test-Path $cacheDir) {
    $pendingChunks = Get-ChildItem $cacheDir -Recurse -File | Where-Object { $_.Length -gt 10MB }
    Write-Host ""
    Write-Host "--- Cache pending chunks ---"
    if ($pendingChunks.Count -eq 0) {
        Write-Host "None"
    } else {
        $pendingChunks | ForEach-Object { Write-Host "  $($_.FullName) ($([math]::Round($_.Length/1MB,2)) MB)" }
    }
}
