#!/usr/bin/env python3
"""质量诊断：3个方向同时测试"""
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

def run(label, first, last, prompt, w, h, steps, cfg, shift):
    print(f"\n{'='*50}")
    print(f"TEST: {label}")
    print(f"  {w}x{h}, steps={steps}, cfg={cfg}, shift={shift}")
    print(f"{'='*50}")
    with open(WORKFLOW, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)
    wf["9"]["inputs"]["image"] = first
    wf["10"]["inputs"]["image"] = last
    wf["7"]["inputs"]["text"] = prompt
    wf["11"]["inputs"]["width"] = w
    wf["11"]["inputs"]["height"] = h
    wf["11"]["inputs"]["length"] = 81
    wf["5"]["inputs"]["shift"] = shift
    wf["6"]["inputs"]["shift"] = shift
    split = steps // 2
    for n in ["12", "13"]:
        wf[n]["inputs"]["steps"] = steps
        wf[n]["inputs"]["cfg"] = cfg
    wf["12"]["inputs"]["end_at_step"] = split
    wf["13"]["inputs"]["start_at_step"] = split
    wf["16"]["inputs"]["filename_prefix"] = f"test_{label}"
    
    pid = queue_prompt(wf)
    print(f"  Queued: {pid}")
    result = wait(pid, timeout=1800)
    if not result:
        print(f"  [ERR] Timeout")
        return None
    for nid, out in result.get("outputs", {}).items():
        items = out.get("videos", []) or out.get("images", []) or out.get("gifs", [])
        for v in items:
            src = COMFYUI_OUTPUT / v["filename"]
            dst = OUTPUT_DIR / f"{label}.mp4"
            shutil.copy2(src, dst)
            print(f"  [OK] {dst.name} ({dst.stat().st_size//1024}KB)")
            return str(dst)
    print(f"  [ERR] No output")
    return None

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
try:
    r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
    print(f"ComfyUI OK | VRAM: {json.loads(r.read())['devices'][0]['vram_free']/1e9:.1f}GB")
except:
    print("ComfyUI down!"); exit(1)

first = "v4_s01_first_00001_.png"
last = "v4_s01_last_00001_.png"

PROMPT_RICH = (
    "cinematic anime masterpiece, best quality, 1boy, young man with short black hair, "
    "white school uniform shirt, dark tie, standing at school gate, "
    "slowly reaching hand up to catch a single falling cherry blossom petal, "
    "gentle spring breeze, dozens of pink petals floating in air, "
    "golden hour warm sunlight casting long shadows, "
    "detailed face with sharp eyes and soft expression, "
    "fine hair strands visible, fabric wrinkles on shirt, "
    "bokeh background with school building and cherry trees, "
    "film grain, depth of field, professional anime lighting, "
    "smooth continuous motion, no scene cut, 5 second shot"
)

PROMPT_SIMPLE = (
    "anime scene, young man in white school uniform slowly raises hand "
    "to catch falling cherry blossom petal, gentle wind, petals floating, "
    "warm afternoon light, detailed face, smooth motion, 5 second shot"
)

# Test D: Rich prompt (same resolution, same params)
run("rich_prompt", first, last, PROMPT_RICH, 480, 832, 22, 4.0, 8.0)

# Test E: Higher resolution 720p
run("hires_720p", first, last, PROMPT_RICH, 624, 1088, 22, 4.0, 8.0)

# Test F: Rich prompt + higher steps + higher shift for more motion
run("rich_motion", first, last, PROMPT_RICH, 480, 832, 30, 5.5, 12.0)

print(f"\n{'='*50}")
print(f"ALL DONE! Results in {OUTPUT_DIR}")
print(f"{'='*50}")
