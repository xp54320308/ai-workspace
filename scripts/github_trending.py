import urllib.request
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = 'https://github.com/trending?since=daily'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')

articles = re.findall(r'<article class="Box-row">(.*?)</article>', html, re.DOTALL)
for i, art in enumerate(articles[:25]):
    # Get repo link from h2
    repo_match = re.search(r'<h2[^>]*>.*?href="(/[^"]+)"', art, re.DOTALL)
    
    # Get description
    desc_match = re.search(r'<p class="col-9[^"]*">\s*(.*?)\s*</p>', art, re.DOTALL)
    
    # Get language
    lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)', art)
    
    # Get stars today
    stars_match = re.search(r'([\d,]+)\s+stars today', art)
    if not stars_match:
        stars_match = re.search(r'([\d,]+)\s+stars', art)
    
    repo = repo_match.group(1).strip() if repo_match else 'unknown'
    desc = desc_match.group(1).strip() if desc_match else ''
    desc = re.sub(r'<[^>]+>', '', desc).strip()
    lang = lang_match.group(1).strip() if lang_match else ''
    stars = stars_match.group(1) if stars_match else ''
    
    print(f'{i+1}. {repo} ({lang}) +{stars} stars')
    if desc:
        print(f'   {desc[:150]}')
    print()
