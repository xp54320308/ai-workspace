$ErrorActionPreference = "SilentlyContinue"
$ts = [int][double]::Parse((Get-Date -UFormat %s))
$threeDaysAgo = $ts - 259200

$queries = @("AI+LLM", "OpenAI", "Anthropic", "Claude", "Gemini", "AI+agent", "GPT")

foreach ($q in $queries) {
    $hnUrl = "https://hn.algolia.com/api/v1/search?query=$q&tags=story&hitsPerPage=5&numericFilters=created_at_i>$threeDaysAgo"
    try {
        $r = Invoke-WebRequest -Uri $hnUrl -UseBasicParsing -TimeoutSec 10
        $d = $r.Content | ConvertFrom-Json
        if ($d.nbHits -gt 0) {
            Write-Output "=== $q ($($d.nbHits) hits) ==="
            foreach ($h in $d.hits) {
                Write-Output "[$($h.points) pts] $($h.title) | $($h.url)"
            }
            Write-Output ""
        }
    } catch {}
}
