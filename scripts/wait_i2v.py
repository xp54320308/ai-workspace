import json, urllib.request, time, shutil, os, subprocess, sys

COMFYUI_URL = 'http://127.0.0.1:8188'
COMFYUI_OUTPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
OUTPUT_DIR = r'C:\Users\qw\.openclaw\workspace\pipeline_test'

pid = '6394cc18-686a-4e75-b5f3-2c9cf8d538b3'
print(f"Waiting for I2V: {pid}", flush=True)

for i in range(90):  # up to 15 min
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if pid in history:
            entry = history[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                print(f"ERROR: {msgs[:5]}", flush=True)
                sys.exit(1)
            outputs = entry.get("outputs", {})
            # Find video output
            for node_id, node_out in outputs.items():
                if "gifs" in node_out:
                    for gif in node_out["gifs"]:
                        src = os.path.join(COMFYUI_OUTPUT, gif["filename"])
                        dst = os.path.join(OUTPUT_DIR, gif["filename"])
                        shutil.copy2(src, dst)
                        print(f"DONE: {dst} ({os.path.getsize(dst)/1024/1024:.1f}MB)", flush=True)
                if "images" in node_out:
                    for img in node_out["images"]:
                        src = os.path.join(COMFYUI_OUTPUT, img["filename"])
                        dst = os.path.join(OUTPUT_DIR, img["filename"])
                        if os.path.exists(src):
                            shutil.copy2(src, dst)
                            print(f"FRAME: {dst}", flush=True)
            print("I2V COMPLETE", flush=True)
            sys.exit(0)
        if i % 6 == 0:
            req2 = urllib.request.Request(f"{COMFYUI_URL}/queue")
            resp2 = urllib.request.urlopen(req2, timeout=10)
            q = json.loads(resp2.read())
            r = len(q.get("queue_running", []))
            p = len(q.get("queue_pending", []))
            print(f"[{i*10}s] Queue: {r}R/{p}P", flush=True)
    except Exception as e:
        print(f"[{i*10}s] {e}", flush=True)
    time.sleep(10)

print("TIMEOUT", flush=True)
