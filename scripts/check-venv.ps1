if (Test-Path "G:\AI\Sana\venv\Scripts\python.exe") {
    Write-Host "Found venv in G:\AI\Sana\venv"
    & "G:\AI\Sana\venv\Scripts\python.exe" --version
    & "G:\AI\Sana\venv\Scripts\pip.exe" list 2>$null | Select-String "torch|diffusers|transformers|xformers|flash|triton|pyrallis|safetensors|einops|timm|sentencepiece"
} else {
    Write-Host "No venv found"
}

Write-Host ""
Write-Host "--- Checking for conda ---"
conda --version 2>$null
if ($LASTEXITCODE -eq 0) {
    conda env list 2>$null
}

Write-Host ""
Write-Host "--- Python launcher ---"
py -0 2>$null
