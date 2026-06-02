$base = 'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models'
$dirs = Get-ChildItem $base -Directory -ErrorAction SilentlyContinue
foreach ($d in $dirs) {
    $files = Get-ChildItem $d.FullName -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '\.(safetensors|ckpt|pt|pth|bin|onnx|gguf)$' }
    if ($files.Count -gt 0) {
        Write-Output "=== $($d.Name) ($($files.Count) files) ==="
        foreach ($f in $files) {
            $sizeMB = [math]::Round($f.Length/1MB, 1)
            $rel = $f.FullName.Replace($d.FullName, '').TrimStart('\')
            Write-Output "  $rel | ${sizeMB}MB"
        }
        Write-Output ""
    }
}
