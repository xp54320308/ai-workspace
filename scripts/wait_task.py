import json
import urllib.request
import time
import sys

prompt_id = sys.argv[1] if len(sys.argv) > 1 else ""
timeout_min = int(sys.argv[2]) if len(sys.argv) > 2 else 5

for i in range(timeout_min * 6):
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            print("DONE", flush=True)
            print(json.dumps(outputs, indent=2), flush=True)
            sys.exit(0)
        # Check queue
        req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        queue = json.loads(resp2.read())
        running = len(queue.get("queue_running", []))
        pending = len(queue.get("queue_pending", []))
        print(f"[{i*10}s] Running: {running}, Pending: {pending}", flush=True)
    except Exception as e:
        print(f"[{i*10}s] Error: {e}", flush=True)
    time.sleep(10)

print("TIMEOUT", flush=True)
