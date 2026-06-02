import json
import urllib.request
import time
import sys

pid = "f6414aec-d43f-40a3-9a29-24dfd274e814"
for i in range(30):
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if pid in history:
            outputs = history[pid].get("outputs", {})
            imgs = outputs.get("9", {}).get("images", [])
            print(f"DONE: {imgs[0]['filename'] if imgs else 'unknown'}", flush=True)
            sys.exit(0)
        req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        q = json.loads(resp2.read())
        r = len(q.get("queue_running", []))
        p = len(q.get("queue_pending", []))
        print(f"[{i*10}s] Queue: {r} running, {p} pending", flush=True)
    except Exception as e:
        print(f"[{i*10}s] {e}", flush=True)
    time.sleep(10)
