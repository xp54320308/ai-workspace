import json
import urllib.request
import time
import sys

prompt_id = "15a3b102-50e3-49e0-9558-83e53aeffcfa"

for i in range(60):
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if prompt_id in history:
            entry = history[prompt_id]
            outputs = entry.get("outputs", {})
            print("DONE")
            print(json.dumps(outputs, indent=2))
            sys.exit(0)
        
        # Check queue
        req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        queue = json.loads(resp2.read())
        running = queue.get("queue_running", [])
        pending = queue.get("queue_pending", [])
        print(f"[{i}] Running: {len(running)}, Pending: {len(pending)}")
    except Exception as e:
        print(f"[{i}] Error: {e}")
    
    time.sleep(10)

print("TIMEOUT - still running after 10 minutes")
