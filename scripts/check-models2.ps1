$ditFile = Get-Item "G:\AI\models\SANA-WM_bidirectional\dit\sana_wm_1600m_720p.safetensors"
Write-Host "dit file size: $([math]::Round($ditFile.Length/1GB,2)) GB"
Write-Host "Last modified: $($ditFile.LastWriteTime)"

$cacheChunk = Get-Item "G:\AI\models\SANA-WM_bidirectional\.cache\huggingface\download\dit\ZXGfFesnqp5aNS3n3sWQkNqtOQU=.93a20c3fc184c44299234b0ed78b5895030533ff453fca2b66f9ed391e0ac258.incomplete" -EA SilentlyContinue
if ($cacheChunk) {
    Write-Host "Cache chunk: $([math]::Round($cacheChunk.Length/1MB,2)) MB"
    if ($cacheChunk.Length -lt $ditFile.Length) {
        Write-Host "=> Cache chunk is smaller than final file => leftover partial download"
    }
}

$teChunk = Get-Item "G:\AI\models\SANA-WM_bidirectional\.cache\huggingface\download\refiner\text_encoder\JPIYbabm4vDoeFTrDUtltbMIGtA=.cbc6e8132e4998652d4c8c219f0ca8da10a143606c806c8728a7513d49bbcdb3.incomplete" -EA SilentlyContinue
if ($teChunk) {
    Write-Host "TE cache chunk: $([math]::Round($teChunk.Length/1MB,2)) MB"
}

# Expected dit size for SANA-WM bidirectional 720p is ~9.92GB (matches)
# Check if all refiner shards have non-zero size
$shards = Get-ChildItem "G:\AI\models\SANA-WM_bidirectional\refiner\text_encoder" -Filter "model-*-of-00011.safetensors"
Write-Host "`n--- Shard sizes ---"
$shards | ForEach-Object {
    Write-Host "$($_.Name): $([math]::Round($_.Length/1GB,2)) GB"
}
