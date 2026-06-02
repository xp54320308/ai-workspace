$ids = @(48232118,48225297,48209691,48231938,48231319,48227397,48232060,48184402,48228788,48229319,48227860,48192605,48209706,48223362,48209905,48222733,48193932,48220696,48220639,48220647,48225357,48225040,48227923,48225426,48196897,48226588,48222529,48219992,48225838,48220105)
foreach ($id in $ids) {
    try {
        $r = Invoke-RestMethod -Uri ("https://hacker-news.firebaseio.com/v0/item/{0}.json" -f $id) -TimeoutSec 5
        $score = if ($r.score) { $r.score } else { 0 }
        $title = if ($r.title) { $r.title } else { "N/A" }
        $url = if ($r.url) { $r.url } else { "text post" }
        Write-Output ("{0}|{1}|{2}|{3}" -f $id, $score, $title, $url)
    } catch { }
}
