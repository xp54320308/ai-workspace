#!/usr/bin/env python3
"""Poll ComfyUI for completion"""
import json, urllib.request, time

prompt_id = "24f1e8e4-73e3-4222-bd0f-4180fa3c33b8"

for i in range(120):
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
                    for img in out.get("images", []):
                        print(f"  Image: {img.get('filename', '?')}")
                break
            elif s.get("status_str") == "error":
                print("ERROR!")
                for m in s.get("messages", []):
                    print(f"  {m}")
                break
            else:
                if i % 3 == 0:
                    print(f"Step {i}... ({i*10}s)")
        else:
            q = json.loads(urllib.request.urlopen("http://127.0.0.1:8188/queue").read())
            running = len(q.get("queue_running", []))
            pending = len(q.get("queue_pending", []))
            if i % 3 == 0:
                print(f"Queue: {running} running, {pending} pending ({i*10}s)")
    except Exception as e:
        if i % 3 == 0:
            print(f"Poll {i}: {e}")
else:
    print("Timeout")
