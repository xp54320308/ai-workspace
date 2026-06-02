import json
import urllib.request
import time
import sys

prompt_ids = json.loads(sys.argv[1])
total = len(prompt_ids)
done_set = set()

for i in range(60):
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        
        for p in prompt_ids:
            if p["id"] in history and p["id"] not in done_set:
                done_set.add(p["id"])
                outputs = history[p["id"]].get("outputs", {})
                imgs = outputs.get("9", {}).get("images", [])
                fname = imgs[0]["filename"] if imgs else "unknown"
                print(f"DONE [{len(done_set)}/{total}]: {p['name']} -> {fname}", flush=True)
        
        if len(done_set) >= total:
            print(f"\nALL DONE! {total} images generated.", flush=True)
            sys.exit(0)
        
        req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        queue = json.loads(resp2.read())
        running = len(queue.get("queue_running", []))
        pending = len(queue.get("queue_pending", []))
        print(f"[{i*10}s] Done: {len(done_set)}/{total}, Queue: {running} running, {pending} pending", flush=True)
    except Exception as e:
        print(f"[{i*10}s] Error: {e}", flush=True)
    time.sleep(10)

print("TIMEOUT", flush=True)
