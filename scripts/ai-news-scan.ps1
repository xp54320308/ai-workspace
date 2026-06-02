$ErrorActionPreference = "SilentlyContinue"

# Calculate 3 days ago timestamp
$now = [int][double]::Parse((Get-Date -UFormat %s))
$threeDaysAgo = $now - 259200

# Search Hacker News for AI/LLM news
$hnUrl = "https://hn.algolia.com/api/v1/search?query=AI+LLM+artificial+intelligence&tags=story&hitsPerPage=15&numericFilters=created_at_i>$threeDaysAgo"

try {
    $response = Invoke-WebRequest -Uri $hnUrl -UseBasicParsing -TimeoutSec 15
    $data = $response.Content | ConvertFrom-Json

    Write-Output "=== Hacker News AI/LLM News ==="
    foreach ($h in $data.hits) {
        $title = $h.title
        $points = $h.points
        $url = $h.url
        $comments = $h.num_comments
        Write-Output "- [$points pts, $comments comments] $title | $url"
    }
} catch {
    Write-Output "HN fetch failed: $_"
}

# Search for OpenAI/Anthropic/Google AI news
$hnUrl2 = "https://hn.algolia.com/api/v1/search?query=OpenAI+Anthropic+Claude+GPT+Gemini+deep+learning&tags=story&hitsPerPage=10&numericFilters=created_at_i>$threeDaysAgo"

try {
    $response2 = Invoke-WebRequest -Uri $hnUrl2 -UseBasicParsing -TimeoutSec 15
    $data2 = $response2.Content | ConvertFrom-Json

    Write-Output "`n=== Company AI News ==="
    foreach ($h in $data2.hits) {
        $title = $h.title
        $points = $h.points
        $url = $h.url
        Write-Output "- [$points pts] $title | $url"
    }
} catch {
    Write-Output "Company news fetch failed: $_"
}

# Search for AI agents, MCP, coding news
$hnUrl3 = "https://hn.algolia.com/api/v1/search?query=AI+agent+coding+MCP+model+context+protocol&tags=story&hitsPerPage=10&numericFilters=created_at_i>$threeDaysAgo"

try {
    $response3 = Invoke-WebRequest -Uri $hnUrl3 -UseBasicParsing -TimeoutSec 15
    $data3 = $response3.Content | ConvertFrom-Json

    Write-Output "`n=== AI Agents & Tools ==="
    foreach ($h in $data3.hits) {
        $title = $h.title
        $points = $h.points
        $url = $h.url
        Write-Output "- [$points pts] $title | $url"
    }
} catch {
    Write-Output "Agent news fetch failed: $_"
}
