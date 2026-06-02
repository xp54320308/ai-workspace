Write-Host "--- Python 3.11 via Astral ---"
py -3.11 --version
py -3.11 -m pip list 2>$null | Select-String "torch|diffusers|transformers|xformers|flash|triton|pyrallis|safetensors|einops|timm|sentencepiece|imageio"
