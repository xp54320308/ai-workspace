$src = 'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
$dst = 'C:\Users\qw\.openclaw\workspace'
$files = @('hidream_ice_queen_00001_.png','hidream_space_battle_00001_.png','hidream_dragon_temple_00001_.png','hidream_neon_city_00001_.png')
foreach ($f in $files) {
    Copy-Item (Join-Path $src $f) (Join-Path $dst $f)
    Write-Output "Copied: $f"
}
