import json, urllib.request
BASE = "http://127.0.0.1:8188"
hist = json.loads(urllib.request.urlopen(f"{BASE}/history", timeout=30).read())
for pid in list(hist.keys())[-5:]:
    h = hist[pid]
    status = h.get("status", {})
    if status.get("status_str") == "error":
        msgs = status.get("messages", [])
        for m in msgs:
            if m[0] == "execution_error":
                print(json.dumps(m[1], indent=2)[:1000])
