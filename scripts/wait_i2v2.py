import json, urllib.request, time, shutil, os, sys

COMFYUI_URL = 'http://127.0.0.1:8188'
COMFYUI_OUTPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
OUTPUT_DIR = r'C:\Users\qw\.openclaw\workspace\pipeline_test'

pid = 'fe5a3af8-5292-4d54-b13e-721af6e87a40'
print(f"Waiting for I2V: {pid}", flush=True)

for i in range(90):
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if pid in history:
            entry = history[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                for m in msgs:
                    if isinstance(m, list) and len(m) > 1:
                        detail = m[1]
                        print(f"ERROR: {detail.get('node_type', '?')} - {detail.get('exception_message', '?')}", flush=True)
                sys.exit(1)
            outputs = entry.get("outputs", {})
            for node_id, node_out in outputs.items():
                for key in ["gifs", "images"]:
                    if key in node_out:
                        for f in node_out[key]:
                            src = os.path.join(COMFYUI_OUTPUT, f["filename"])
                            dst = os.path.join(OUTPUT_DIR, f["filename"])
                            if os.path.exists(src):
                                shutil.copy2(src, dst)
                                sz = os.path.getsize(dst) / 1024 / 1024
                                print(f"DONE: {f['filename']} ({sz:.1f}MB)", flush=True)
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
