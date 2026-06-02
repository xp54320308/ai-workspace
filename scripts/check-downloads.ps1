$files = Get-ChildItem -Path 'F:\Comfyui\ComfyUI-aki-v3\models' -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*t5xxl*' -or $_.Name -like '*hidream*' -or ($_.Name -like '*llama*' -and $_.Name -like '*8b*') }
foreach ($f in $files) {
    $sizeMB = [math]::Round($f.Length/1MB, 1)
    Write-Output "$($f.FullName) | ${sizeMB}MB | $($f.LastWriteTime)"
}
