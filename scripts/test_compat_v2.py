#!/usr/bin/env python3
"""质量测试 v2：兼容采样器 + 提升步数/CFG"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test")

def queue_prompt(wf):
    body = json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode()
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["prompt_id"]

def wait(pid, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{urllib.parse.quote(pid)}", timeout=30) as r:
                h = json.loads(r.read())
                if pid in h:
                    return h[pid]
        except: pass
        time.sleep(5)
    return None

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
    stats = json.loads(r.read())
    print(f"ComfyUI OK | VRAM: {stats['devices'][0]['vram_free']/1e9:.1f}GB free")
except:
    print("ComfyUI not available!")
    exit(1)

first = "v4_s01_first_00001_.png"
last = "v4_s01_last_00001_.png"

# ===== 测试 C: euler + simple + steps=30 + cfg=5.5 =====
print(f"\n{'='*50}")
print(f"TEST C: euler + simple, steps=30, cfg=5.5")
print(f"{'='*50}")

with open(WORKFLOW, "r", encoding="utf-8-sig") as f:
    wf = json.load(f)

wf["9"]["inputs"]["image"] = first
wf["10"]["inputs"]["image"] = last
wf["7"]["inputs"]["text"] = (
    "anime scene, young man in white school uniform slowly raises hand "
    "to catch falling cherry blossom petal, gentle wind, petals floating, "
    "warm afternoon light, detailed face, smooth motion, 5 second shot"
)
wf["11"]["inputs"]["width"] = 480
wf["11"]["inputs"]["height"] = 832
wf["11"]["inputs"]["length"] = 81

# Keep compatible sampler, just boost steps + cfg
steps = 30
split = 15
wf["12"]["inputs"]["steps"] = steps
wf["12"]["inputs"]["cfg"] = 5.5
wf["12"]["inputs"]["end_at_step"] = split
wf["13"]["inputs"]["steps"] = steps
wf["13"]["inputs"]["cfg"] = 5.5
wf["13"]["inputs"]["start_at_step"] = split

wf["16"]["inputs"]["filename_prefix"] = "test_compat_v2"

pid = queue_prompt(wf)
print(f"  Prompt ID: {pid}")
print(f"  Waiting...")

result = wait(pid, timeout=1800)
if not result:
    print(f"  [ERR] Timeout")
    exit(1)

outputs = result.get("outputs", {})
for nid, out in outputs.items():
    items = out.get("videos", []) or out.get("images", []) or out.get("gifs", [])
    for v in items:
        fname = v["filename"]
        src = COMFYUI_OUTPUT / fname
        dst = OUTPUT_DIR / "compat_euler30.mp4"
        shutil.copy2(src, dst)
        print(f"  [OK] {dst} ({dst.stat().st_size//1024}KB)")
        print(f"\nDONE! Compare: old_params.mp4 vs compat_euler30.mp4")
        exit(0)

print(f"  [ERR] No output found")
exit(1)
