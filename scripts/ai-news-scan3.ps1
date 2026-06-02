$ErrorActionPreference = "SilentlyContinue"

# Get recent HN stories from last 3 days
$ts = [int][double]::Parse((Get-Date -UFormat %s))
$threeDaysAgo = $ts - 259200
$hnUrl = "https://hn.algolia.com/api/v1/search?query=AI+LLM+model+agent&tags=story&hitsPerPage=30&numericFilters=created_at_i>$threeDaysAgo&restrictSearchAttributes=title"
try {
    $r = Invoke-WebRequest -Uri $hnUrl -UseBasicParsing -TimeoutSec 15
    $d = $r.Content | ConvertFrom-Json
    Write-Output "Total recent AI hits: $($d.nbHits)"
    foreach ($h in $d.hits) {
        Write-Output "[$($h.points) pts] $($h.title) | $($h.url) | $($h.created_at)"
    }
} catch { Write-Output "Failed: $_" }

Write-Output "`n=== OpenAI/Anthropic/Google ==="
$hnUrl2 = "https://hn.algolia.com/api/v1/search?query=OpenAI+Anthropic+Google+Gemini+Claude+GPT&tags=story&hitsPerPage=20&numericFilters=created_at_i>$threeDaysAgo&restrictSearchAttributes=title"
try {
    $r2 = Invoke-WebRequest -Uri $hnUrl2 -UseBasicParsing -TimeoutSec 15
    $d2 = $r2.Content | ConvertFrom-Json
    Write-Output "Company hits: $($d2.nbHits)"
    foreach ($h in $d2.hits) {
        Write-Output "[$($h.points) pts] $($h.title) | $($h.url)"
    }
} catch { Write-Output "Failed: $_" }

Write-Output "`n=== Coding/Agents/MCP ==="
$hnUrl3 = "https://hn.algolia.com/api/v1/search?query=coding+agent+MCP+Copilot+Cursor&tags=story&hitsPerPage=15&numericFilters=created_at_i>$threeDaysAgo&restrictSearchAttributes=title"
try {
    $r3 = Invoke-WebRequest -Uri $hnUrl3 -UseBasicParsing -TimeoutSec 15
    $d3 = $r3.Content | ConvertFrom-Json
    Write-Output "Coding hits: $($d3.nbHits)"
    foreach ($h in $d3.hits) {
        Write-Output "[$($h.points) pts] $($h.title) | $($h.url)"
    }
} catch { Write-Output "Failed: $_" }

Write-Output "`n=== Open Source AI ==="
$hnUrl4 = "https://hn.algolia.com/api/v1/search?query=open+source+model+release+launch&tags=story&hitsPerPage=15&numericFilters=created_at_i>$threeDaysAgo&restrictSearchAttributes=title"
try {
    $r4 = Invoke-WebRequest -Uri $hnUrl4 -UseBasicParsing -TimeoutSec 15
    $d4 = $r4.Content | ConvertFrom-Json
    Write-Output "Open source hits: $($d4.nbHits)"
    foreach ($h in $d4.hits) {
        Write-Output "[$($h.points) pts] $($h.title) | $($h.url)"
    }
} catch { Write-Output "Failed: $_" }
