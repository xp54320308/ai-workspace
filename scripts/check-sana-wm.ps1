# Fetch PR #379 status
try {
    $prs = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/pulls/379" -TimeoutSec 10
    Write-Host "PR #379 Status: $($prs.state)"
    Write-Host "Title: $($prs.title)"
    Write-Host "Created: $($prs.created_at)"
    Write-Host "Updated: $($prs.updated_at)"
    Write-Host "Merged: $($prs.merged)"
    Write-Host "Mergeable state: $($prs.mergeable_state)"
    Write-Host "Commits: $($prs.commits)"
    Write-Host "Changed files: $($prs.changed_files)"
} catch {
    Write-Host "API Error: $($_.Exception.Message)"
}

# Check main branch
try {
    $files = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/contents/inference_video_scripts" -TimeoutSec 10
    Write-Host ""
    Write-Host "--- inference_video_scripts on main branch ---"
    $files | ForEach-Object { Write-Host "  $($_.name)" }
} catch {
    Write-Host "Error checking main branch"
}

# Check feat/sana-wm branch
try {
    $files2 = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/contents/inference_video_scripts?ref=feat/sana-wm" -TimeoutSec 10
    Write-Host ""
    Write-Host "--- inference_video_scripts on feat/sana-wm ---"
    $files2 | ForEach-Object { Write-Host "  $($_.name)" }
} catch {
    Write-Host "feat/sana-wm branch: error or not found"
}

# Check latest commits on feat/sana-wm
try {
    $commits = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/commits?sha=feat/sana-wm&per_page=5" -TimeoutSec 10
    Write-Host ""
    Write-Host "--- Latest commits on feat/sana-wm ---"
    $commits | ForEach-Object {
        Write-Host "  $($_.sha.Substring(0,7)) $($_.commit.message.Substring(0, [Math]::Min(80, $_.commit.message.Length)))"
    }
} catch {
    Write-Host "Error checking commits"
}
