# Try fetching the PR directly
Write-Host "Cloning NVlabs/Sana (main)..."
git clone https://github.com/NVlabs/Sana.git G:\AI\Sana 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Clone failed"
    exit 1
}

cd G:\AI\Sana

Write-Host "Fetching PR #379..."
git fetch origin pull/379/head:feat/sana-wm 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "Switching to feat/sana-wm..."
    git checkout feat/sana-wm 2>&1
    Write-Host "Done! Current branch:"
    git branch
} else {
    Write-Host "Failed to fetch PR, trying head SHA directly..."
    git fetch origin 48bba61ecb86c40f663a2f125dd344ac9e35444f 2>&1
    git checkout 48bba61ecb86c40f663a2f125dd344ac9e35444f 2>&1
}
