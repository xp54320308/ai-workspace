$base = 'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models'
$patterns = @('*t5xxl*', '*hidream*', '*llama*')
$found = @()
foreach ($p in $patterns) {
    $found += Get-ChildItem -Path $base -Recurse -Include $p -File -ErrorAction SilentlyContinue
}
foreach ($f in $found) {
    $sizeMB = [math]::Round($f.Length/1MB, 1)
    Write-Output "$($f.Name) | ${sizeMB}MB | $($f.Directory.Name)"
}
