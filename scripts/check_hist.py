import json, urllib.request
BASE = "http://127.0.0.1:8188"
hist = json.loads(urllib.request.urlopen(f"{BASE}/history", timeout=30).read())
for pid in list(hist.keys())[-3:]:
    h = hist[pid]
    status = h.get("status", {})
    outputs = h.get("outputs", {})
    print(f"pid: {pid[:16]}... status: {status.get('status_str')}")
    for nid, out in outputs.items():
        imgs = out.get("images", [])
        gifs = out.get("gifs", [])
        vids = out.get("videos", [])
        if imgs or gifs or vids:
            print(f"  node {nid}: images={len(imgs)} gifs={len(gifs)} videos={len(vids)}")
            for g in gifs:
                print(f"    gif: {g}")
            for v in vids:
                print(f"    video: {v}")
            for i in imgs:
                print(f"    img: {i}")
