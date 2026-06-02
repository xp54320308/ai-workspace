#!/usr/bin/env python3
import json, urllib.request, time

prompt_id = "558a5d62-af7d-4ff9-9766-3fc528932b8b"
print(f"Polling {prompt_id}...")

for i in range(180):
    time.sleep(10)
    try:
        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{prompt_id}").read())
        if prompt_id in h:
            s = h[prompt_id].get("status", {})
            if s.get("completed"):
                print("COMPLETED!")
                for nid, out in h[prompt_id].get("outputs", {}).items():
                    for g in out.get("gifs", []):
                        print(f"  Video: {g.get('filename', '?')}")
                break
            elif s.get("status_str") == "error":
                print("ERROR!")
                for m in s.get("messages", []):
                    print(f"  {m}")
                break
            else:
                if i % 3 == 0:
                    print(f"Running... {i*10}s")
        else:
            q = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/queue").read())
            r = len(q.get("queue_running", []))
            p = len(q.get("queue_pending", []))
            if i % 3 == 0:
                print(f"Queue: {r} running, {p} pending ({i*10}s)")
    except Exception as e:
        if i % 3 == 0:
            print(f"Poll {i}: {e}")
else:
    print("Timeout")
