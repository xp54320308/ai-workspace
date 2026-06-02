$ErrorActionPreference = "SilentlyContinue"

# Try simpler HN search - front page stories with AI
$hnUrl = "https://hn.algolia.com/api/v1/search?query=AI&tags=story&hitsPerPage=20"

try {
    $response = Invoke-WebRequest -Uri $hnUrl -UseBasicParsing -TimeoutSec 15
    $data = $response.Content | ConvertFrom-Json

    Write-Output "=== HN AI Stories (recent) ==="
    $i = 0
    foreach ($h in $data.hits) {
        $i++
        if ($i -gt 20) { break }
        $title = $h.title
        $points = $h.points
        $url = $h.url
        $created = $h.created_at
        Write-Output "$i. [$points pts] $title ($created) | $url"
    }
    Write-Output "Total: $($data.nbHits) hits"
} catch {
    Write-Output "HN fetch failed: $_"
}

Write-Output "`n=== Trying arXiv AI papers ==="
$arxivUrl = "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5"
try {
    $r2 = Invoke-WebRequest -Uri $arxivUrl -UseBasicParsing -TimeoutSec 15
    $xml = [xml]$r2.Content
    foreach ($entry in $xml.feed.entry) {
        $t = $entry.title -replace '\s+', ' '
        Write-Output "- $($t.Trim())"
        Write-Output "  $($entry.id)"
    }
} catch {
    Write-Output "arXiv fetch failed: $_"
}
