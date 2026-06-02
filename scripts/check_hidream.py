import json
import urllib.request
import sys

prompt_id = "15a3b102-50e3-49e0-9558-83e53aeffcfa"

# Check history
try:
    req = urllib.request.Request("http://127.0.0.1:8188/history")
    resp = urllib.request.urlopen(req, timeout=10)
    history = json.loads(resp.read())
    if prompt_id in history:
        entry = history[prompt_id]
        outputs = entry.get("outputs", {})
        status_info = entry.get("status", {})
        print("STATUS: DONE", flush=True)
        print(json.dumps(outputs, indent=2), flush=True)
    else:
        print("STATUS: NOT_FOUND_IN_HISTORY", flush=True)
except Exception as e:
    print(f"Error checking history: {e}", flush=True)

# Check queue
try:
    req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
    resp2 = urllib.request.urlopen(req2, timeout=10)
    queue = json.loads(resp2.read())
    running = queue.get("queue_running", [])
    pending = queue.get("queue_pending", [])
    print(f"Queue - Running: {len(running)}, Pending: {len(pending)}", flush=True)
    for r in running:
        print(f"  Running: {r}", flush=True)
except Exception as e:
    print(f"Error checking queue: {e}", flush=True)
