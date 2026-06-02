$ErrorActionPreference = "Stop"
$xml = [xml](Invoke-WebRequest -Uri 'https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans' -UseBasicParsing -TimeoutSec 10 -Headers @{'User-Agent'='Mozilla/5.0'}).Content
$xml.rss.channel.item | Select-Object -First 15 | ForEach-Object {
    $title = $_.title -replace ' - [^-]+$',''
    Write-Output $title
}
