$ErrorActionPreference = "SilentlyContinue"

# Try multiple news sources
$urls = @(
    @{ name = "Google News CN"; url = "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans" },
    @{ name = "Zhihu Hot"; url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=20" },
    @{ name = "Weibo Hot"; url = "https://weibo.com/ajax/side/hotSearch" }
)

foreach ($source in $urls) {
    try {
        $resp = Invoke-WebRequest -Uri $source.url -UseBasicParsing -TimeoutSec 10 -Headers @{"User-Agent"="Mozilla/5.0"} 
        Write-Output "=== $($source.name) ==="
        $content = $resp.Content
        if ($content.Length -gt 6000) { $content = $content.Substring(0, 6000) }
        Write-Output $content
        Write-Output ""
    } catch {
        Write-Output "=== $($source.name) FAILED: $($_.Exception.Message) ==="
    }
}
