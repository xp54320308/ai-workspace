import json, urllib.request, time

now = int(time.time())
cutoff = now - 86400 * 3  # last 3 days

queries = [
    "AI LLM",
    "AI agent model",
    "OpenAI Anthropic Google Meta AI",
    "LLM framework open source",
    "machine learning breakthrough",
]

all_hits = {}
for q in queries:
    url = f"https://hn.algolia.com/api/v1/search?query={q.replace(' ', '+')}&tags=story&hitsPerPage=15&numericFilters=created_at_i>{cutoff}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for h in data.get("hits", []):
                oid = h.get("objectID")
                if oid and oid not in all_hits:
                    all_hits[oid] = h
    except Exception as e:
        print(f"Error fetching '{q}': {e}")

# Sort by points desc
sorted_hits = sorted(all_hits.values(), key=lambda x: x.get("points", 0), reverse=True)

for h in sorted_hits[:25]:
    pts = h.get("points", 0)
    title = h.get("title", "")
    url = h.get("url", "")
    hn_url = f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
    comments = h.get("num_comments", 0)
    created = h.get("created_at", "")
    print(f"[{pts}pts | {comments}cmts] {title}")
    print(f"  URL: {url}")
    print(f"  HN: {hn_url}")
    print(f"  Date: {created}")
    print()
