# Hacker News
try {
    $resp = Invoke-WebRequest -Uri 'https://hnrss.org/frontpage' -UseBasicParsing
    $content = $resp.Content
    $titles = [regex]::Matches($content, '<title>([^<]+)</title>') | ForEach-Object { $_.Groups[1].Value } | Select-Object -Skip 1 -First 8
    "=== Hacker News ===" 
    $titles | ForEach-Object { $_ }
} catch {
    "HN Error: $($_.Exception.Message)"
}

# GitHub Trending
try {
    $resp2 = Invoke-WebRequest -Uri 'https://github.com/trending?since=weekly' -UseBasicParsing
    $content2 = $resp2.Content
    $projects = [regex]::Matches($content2, 'href="\/([a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+)"') | ForEach-Object { $_.Groups[1].Value } | Select-Object -First 12
    "`n=== GitHub Weekly Trending ===" 
    $projects | ForEach-Object { $_ }
} catch {
    "GitHub Error: $($_.Exception.Message)"
}
