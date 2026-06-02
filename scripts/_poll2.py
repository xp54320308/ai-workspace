import urllib.request, json, time, os, shutil, sys

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
pid = "248d3301-2d63-4a96-a376-222d27d356ae"

while True:
    try:
        r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
        if pid in r:
            status = r[pid].get("status", {})
            if status.get("completed") or status.get("status_str") == "error":
                print("Status:", status.get("status_str"), flush=True)
                if status.get("status_str") == "error":
                    for m in status.get("messages", []):
                        print("ERR:", json.dumps(m)[:300], flush=True)
                for nid, out in r[pid].get("outputs", {}).items():
                    if out and "gifs" in out:
                        for v in out["gifs"]:
                            src = os.path.join(COMFYUI_OUTPUT, v.get("subfolder", ""), v["filename"])
                            dst = os.path.join(OUTPUT_DIR, "dynamic_video.mp4")
                            shutil.copy2(src, dst)
                            print("Video:", dst, round(os.path.getsize(dst)/1024/1024, 1), "MB", flush=True)
                    elif out and "images" in out:
                        for img in out["images"]:
                            print("Image:", img["filename"], flush=True)
                break
    except:
        pass
    q = json.loads(urllib.request.urlopen(COMFYUI + "/queue").read())
    print("Running:", len(q.get("queue_running", [])), flush=True)
    time.sleep(30)
