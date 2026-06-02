import json, urllib.request, time, sys

cutoff = int(time.time()) - 3 * 86400

queries = [
    "AI LLM",
    "OpenAI Google Anthropic Meta AI",
    "agent coding model release",
]

all_stories = {}

for q in queries:
    url = f"https://hn.algolia.com/api/v1/search?query={q.replace(' ', '+')}&tags=story&hitsPerPage=15&numericFilters=created_at_i>{cutoff}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for h in data.get("hits", []):
                oid = h.get("objectID")
                if oid and oid not in all_stories:
                    all_stories[oid] = {
                        "title": h.get("title", ""),
                        "url": h.get("url", ""),
                        "points": h.get("points", 0),
                        "comments": h.get("num_comments", 0),
                        "created": h.get("created_at", ""),
                    }
    except Exception as e:
        print(f"Error fetching '{q}': {e}", file=sys.stderr)

# Sort by points, top 15
sorted_stories = sorted(all_stories.values(), key=lambda x: x["points"], reverse=True)[:15]

for s in sorted_stories:
    print(f"[{s['points']} pts | {s['comments']} comments] {s['title']}")
    print(f"  {s['url']}")
    print(f"  {s['created']}")
    print()
