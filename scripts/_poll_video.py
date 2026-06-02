import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
pid = "248d3301-2d63-4a96-a376-222d27d356ae"

for i in range(120):
    try:
        r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
        if pid in r and r[pid].get("status", {}).get("completed"):
            print("DONE!")
            status = r[pid]["status"]
            print("Status:", status.get("status_str"))
            outputs = r[pid]["outputs"]
            for nid, out in outputs.items():
                if out and "gifs" in out:
                    for v in out["gifs"]:
                        video_file = v["filename"]
                        subfolder = v.get("subfolder", "")
                        src = os.path.join(COMFYUI_OUTPUT, subfolder, video_file) if subfolder else os.path.join(COMFYUI_OUTPUT, video_file)
                        dst = os.path.join(OUTPUT_DIR, "dynamic_video.mp4")
                        shutil.copy2(src, dst)
                        print("Video:", dst)
                        print("Size:", round(os.path.getsize(dst) / 1024 / 1024, 1), "MB")
                elif out and "images" in out:
                    for img in out["images"]:
                        print("Image:", img["filename"])
            break
        elif pid in r and r[pid].get("status", {}).get("status_str") == "error":
            print("ERROR!")
            msgs = r[pid]["status"].get("messages", [])
            for m in msgs:
                print(json.dumps(m)[:300])
            break
    except Exception as e:
        pass
    q = json.loads(urllib.request.urlopen(COMFYUI + "/queue").read())
    running = len(q.get("queue_running", []))
    pending = len(q.get("queue_pending", []))
    print("[" + str(i*30) + "s] Running:", running, "Pending:", pending)
    time.sleep(30)
else:
    print("Timeout 3600s")
