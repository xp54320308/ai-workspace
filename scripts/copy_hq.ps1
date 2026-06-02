$src = 'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
$dst = 'C:\Users\qw\.openclaw\workspace'
$files = @('hd_landscape_00001_.png','hd_mecha_00001_.png','hd_ocean_00001_.png','hd_food_00001_.png','hd_abstract_00001_.png')
foreach ($f in $files) {
    Copy-Item (Join-Path $src $f) (Join-Path $dst $f)
    Write-Output "Copied: $f"
}
