$urls = @(
  'https://news.sina.com.cn/',
  'https://www.ithome.com/',
  'https://36kr.com/'
)
foreach ($url in $urls) {
  try {
    $r = Invoke-WebRequest -Uri $url -Headers @{'User-Agent'='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'} -TimeoutSec 8 -UseBasicParsing
    Write-Output ('=== ' + $url + ' (len=' + $r.Content.Length + ') ===')
    $matches2 = [regex]::Matches($r.Content, 'title=.([^'']{8,100}).')
    $seen = @{}
    $count = 0
    foreach ($m in $matches2) {
      $t = $m.Groups[1].Value
      if (!$seen.ContainsKey($t) -and $t -notmatch '^\s*$') {
        $seen[$t] = $true
        $count++
        Write-Output ('  ' + $count + '. ' + $t)
        if ($count -ge 8) { break }
      }
    }
    Write-Output ''
  } catch {
    Write-Output ('=== ' + $url + ' ERROR: ' + $_.Exception.Message)
    Write-Output ''
  }
}
