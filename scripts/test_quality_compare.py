#!/usr/bin/env python3
"""质量测试：用相同首尾帧，对比旧参数 vs 新参数"""
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

def run_test(label, first_img, last_img, steps, cfg, sampler, scheduler, shift):
    """跑一个测试，返回输出视频路径"""
    print(f"\n{'='*50}")
    print(f"测试: {label}")
    print(f"  steps={steps}, cfg={cfg}, sampler={sampler}, shift={shift}")
    print(f"  首帧={first_img}, 尾帧={last_img}")
    print(f"{'='*50}")

    with open(WORKFLOW, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)

    # 设置首尾帧
    wf["9"]["inputs"]["image"] = first_img
    wf["10"]["inputs"]["image"] = last_img
    wf["7"]["inputs"]["text"] = (
        "anime scene, young man in white school uniform slowly raises hand "
        "to catch falling cherry blossom petal, gentle wind, petals floating, "
        "warm afternoon light, detailed face, smooth motion, 5 second shot"
    )
    wf["11"]["inputs"]["width"] = 480
    wf["11"]["inputs"]["height"] = 832
    wf["11"]["inputs"]["length"] = 81

    # 质量覆盖
    split = int(steps * 0.5)
    wf["5"]["inputs"]["shift"] = shift
    wf["6"]["inputs"]["shift"] = shift
    wf["12"]["inputs"]["steps"] = steps
    wf["12"]["inputs"]["cfg"] = cfg
    wf["12"]["inputs"]["sampler_name"] = sampler
    wf["12"]["inputs"]["scheduler"] = scheduler
    wf["12"]["inputs"]["end_at_step"] = split
    wf["13"]["inputs"]["steps"] = steps
    wf["13"]["inputs"]["cfg"] = cfg
    wf["13"]["inputs"]["sampler_name"] = sampler
    wf["13"]["inputs"]["scheduler"] = scheduler
    wf["13"]["inputs"]["start_at_step"] = split

    wf["16"]["inputs"]["filename_prefix"] = f"test_{label}"

    pid = queue_prompt(wf)
    print(f"  Prompt ID: {pid}")
    print(f"  等待生成...")

    result = wait(pid, timeout=1800)
    if not result:
        print(f"  [ERR] 超时或失败")
        return None

    outputs = result.get("outputs", {})
    for nid, out in outputs.items():
        # SaveVideo 输出到 images key (animated=true)
        items = out.get("videos", []) or out.get("images", []) or out.get("gifs", [])
        for v in items:
            fname = v["filename"]
            src = COMFYUI_OUTPUT / fname
            dst = OUTPUT_DIR / f"{label}.mp4"
            shutil.copy2(src, dst)
            size_kb = dst.stat().st_size / 1024
            print(f"  [OK] {dst} ({size_kb:.0f}KB)")
            return str(dst)

    print(f"  [FAIL] no output found")
    return None


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 检查 ComfyUI
    try:
        r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        stats = json.loads(r.read())
        vram = stats['devices'][0]['vram_free'] / 1e9
        print(f"ComfyUI OK | VRAM: {vram:.1f}GB free")
    except:
        print("ComfyUI 不可用!")
        exit(1)

    first = "v4_s01_first_00001_.png"
    last = "v4_s01_last_00001_.png"

    # 确认图片存在
    for img in [first, last]:
        if not (COMFYUI_INPUT / img).exists():
            print(f"[ERR] 图片不存在: {img}")
            exit(1)

    # ---- 测试 A: 旧参数（复现当前低质量） ----
    run_test(
        label="old_params",
        first_img=first, last_img=last,
        steps=22, cfg=4.0,
        sampler="euler", scheduler="simple", shift=8.0
    )

    # ---- 测试 B: 新参数（修复后） ----
    run_test(
        label="new_params",
        first_img=first, last_img=last,
        steps=30, cfg=5.5,
        sampler="dpmpp_2m_sde", scheduler="karras", shift=8.0
    )

    print(f"\n{'='*50}")
    print(f"两组测试完成，输出在: {OUTPUT_DIR}")
    print(f"请对比 old_params.mp4 vs new_params.mp4")
    print(f"{'='*50}")

