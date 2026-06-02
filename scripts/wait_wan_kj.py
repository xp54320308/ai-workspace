import json, urllib.request, time, shutil, os, sys

pid = '88139d34-8bc6-4c6d-aced-a7f500b630f3'
COMFYUI_OUTPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
OUTPUT_DIR = r'C:\Users\qw\.openclaw\workspace\pipeline_test'

print(f"Waiting for Wan 2.2 I2V KJ...", flush=True)

for i in range(120):
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        if pid in history:
            entry = history[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                for m in msgs:
                    if isinstance(m, list) and len(m) > 1:
                        d = m[1]
                        nt = d.get('node_type', '')
                        em = d.get('exception_message', '')
                        if nt or em:
                            print(f"ERROR: {nt} - {em}", flush=True)
                sys.exit(1)
            outputs = entry.get("outputs", {})
            for nid, nout in outputs.items():
                for key in ["gifs", "images"]:
                    if key in nout:
                        for f in nout[key]:
                            src = os.path.join(COMFYUI_OUTPUT, f["filename"])
                            dst = os.path.join(OUTPUT_DIR, f["filename"])
                            if os.path.exists(src):
                                shutil.copy2(src, dst)
                                sz = os.path.getsize(dst) / 1024 / 1024
                                print(f"DONE: {f['filename']} ({sz:.1f}MB)", flush=True)
            print("COMPLETE", flush=True)
            sys.exit(0)
        if i % 6 == 0:
            req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
            resp2 = urllib.request.urlopen(req2, timeout=10)
            q = json.loads(resp2.read())
            r = len(q.get("queue_running", []))
            p = len(q.get("queue_pending", []))
            print(f"[{i*10}s] Queue: {r}R/{p}P", flush=True)
    except Exception as e:
        print(f"[{i*10}s] {e}", flush=True)
    time.sleep(10)
