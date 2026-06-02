$content = (Invoke-WebRequest -Uri 'https://github.com/trending?since=daily' -Headers @{'User-Agent'='Mozilla/5.0'} -UseBasicParsing).Content
$articles = $content -split '<article' | Select-Object -Skip 1
foreach ($a in $articles) {
  $h2 = [regex]::Match($a, 'href="(/.*?)"').Groups[1].Value
  $desc = [regex]::Match($a, '(?s)<p class="col-9.*?>(.*?)</p>').Groups[1].Value.Trim()
  $stars = [regex]::Match($a, '([\d,]+)\s*stars today').Groups[1].Value
  $lang = [regex]::Match($a, 'itemprop="programmingLanguage">(.*?)<').Groups[1].Value
  if ($h2) { Write-Output "REPO:$h2|STARS:$stars|LANG:$lang|DESC:$desc" }
}
