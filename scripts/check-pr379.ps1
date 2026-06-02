# Direct check PR #379 status
try {
    $pr = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/pulls/379" -TimeoutSec 15
    Write-Host "PR #379:"
    Write-Host "  State: $($pr.state)"
    Write-Host "  Merged: $($pr.merged)"
    Write-Host "  Merged at: $($pr.merged_at)"
    Write-Host "  Mergeable: $($pr.mergeable)"
    Write-Host "  Mergeable state: $($pr.mergeable_state)"
    Write-Host "  Title: $($pr.title)"
    Write-Host "  User: $($pr.user.login)"
    Write-Host "  Created: $($pr.created_at)"
    Write-Host "  Updated: $($pr.updated_at)"
    Write-Host "  Commits: $($pr.commits)"
    Write-Host "  Changed files: $($pr.changed_files)"
    Write-Host "  Head ref: $($pr.head.ref)"
    Write-Host "  Head sha: $($pr.head.sha)"
    Write-Host "  Base ref: $($pr.base.ref)"
    Write-Host "  Labels: $($pr.labels.name -join ', ')"
} catch {
    Write-Host "Error fetching PR: $($_.Exception.Message)"
}

# Check if the head commit is on main
try {
    $main = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/commits/main" -TimeoutSec 10
    Write-Host ""
    Write-Host "Main branch latest:"
    Write-Host "  SHA: $($main.sha.Substring(0,7))"
    Write-Host "  Message: $($main.commit.message.Substring(0, [Math]::Min(80, $main.commit.message.Length)))"
    Write-Host "  Date: $($main.commit.committer.date)"
} catch {
    Write-Host "Error checking main: $($_.Exception.Message)"
}

# Check recent issues about SANA-WM
try {
    $issues = Invoke-RestMethod -Uri "https://api.github.com/repos/NVlabs/Sana/issues?labels=SANA-WM&state=all&per_page=5" -TimeoutSec 10
    Write-Host ""
    Write-Host "--- SANA-WM labeled issues ---"
    $issues | ForEach-Object {
        Write-Host "  #$($_.number) [$($_.state)] $($_.title)"
    }
} catch {
    Write-Host "No SANA-WM label or error"
}
