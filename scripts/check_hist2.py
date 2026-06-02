import json, urllib.request
BASE = "http://127.0.0.1:8188"
hist = json.loads(urllib.request.urlopen(f"{BASE}/history", timeout=30).read())
for pid in list(hist.keys())[-5:]:
    h = hist[pid]
    status = h.get("status", {})
    if status.get("status_str") == "error":
        print(f"ERROR pid: {pid[:16]}...")
        print(f"  status: {json.dumps(status, indent=2)[:500]}")
        outputs = h.get("outputs", {})
        for nid, out in outputs.items():
            if out.get("images") or out.get("gifs") or out.get("videos"):
                print(f"  node {nid}: {out}")
