$nodes = Get-ChildItem 'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\custom_nodes' -Directory -ErrorAction SilentlyContinue
foreach ($n in $nodes) {
    Write-Output $n.Name
}
