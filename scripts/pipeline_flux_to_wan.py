#!/usr/bin/env python3
"""
Flux 首帧 → Wan I2V 视频 Pipeline
关键改进：用 Flux 生成高质量首尾帧（解决输入质量问题）
"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW_I2V = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test\pipeline_v7")

def queue_prompt(wf, cid=None):
    body = json.dumps({"prompt": wf, "client_id": cid or str(uuid.uuid4())}).encode()
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

def get_output_files(result):
    """从 ComfyUI 结果中提取所有输出文件"""
    files = []
    for nid, out in result.get("outputs", {}).items():
        for key in ["images", "videos", "gifs"]:
            for item in out.get(key, []):
                fname = item["filename"]
                subfolder = item.get("subfolder", "")
                if subfolder:
                    fname = os.path.join(subfolder, fname)
                files.append(COMFYUI_OUTPUT / fname)
    return files


# ============================================================
# Step 1: Flux 生成高质量首帧
# ============================================================
def generate_flux_frame(prompt, output_name, width=480, height=832, steps=25, cfg=3.5, seed=42):
    """用 Flux 1 Dev 生成高质量图片"""
    print(f"\n[Step 1] Flux 生成: {output_name} ({width}x{height})")
    
    # Flux 1 Dev 需要独立加载 UNET + DualCLIP + VAE
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {
            "clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp16.safetensors", "type": "flux"
        }},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 0],
            "latent_image": ["5", 0],
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": output_name}}
    }
    
    pid = queue_prompt(wf, f"flux_{output_name}")
    print(f"  Queued: {pid}")
    result = wait(pid, timeout=600)
    if not result:
        print(f"  [ERR] Timeout")
        return None
    
    files = get_output_files(result)
    if files:
        src = files[0]
        # Copy to ComfyUI input for I2V to use
        dst_input = COMFYUI_INPUT / f"{output_name}.png"
        shutil.copy2(src, dst_input)
        # Copy to output dir
        dst_output = OUTPUT_DIR / f"{output_name}.png"
        shutil.copy2(src, dst_output)
        print(f"  [OK] {dst_output.name} ({dst_output.stat().st_size//1024}KB)")
        return f"{output_name}.png"
    
    print(f"  [ERR] No output")
    return None


# ============================================================
# Step 2: Wan I2V 生成视频
# ============================================================
def generate_wan_video(first_img, last_img, motion_prompt, output_name,
                       width=480, height=832, steps=22, cfg=4.0, shift=12.0):
    """用 Wan 2.2 I2V 生成视频"""
    print(f"\n[Step 2] Wan I2V: {output_name} ({width}x{height}, shift={shift})")
    
    with open(WORKFLOW_I2V, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)
    
    # 首尾帧
    wf["9"]["inputs"]["image"] = first_img
    wf["10"]["inputs"]["image"] = last_img
    # Prompt
    wf["7"]["inputs"]["text"] = motion_prompt
    # 尺寸
    wf["11"]["inputs"]["width"] = width
    wf["11"]["inputs"]["height"] = height
    wf["11"]["inputs"]["length"] = 81
    # 输出
    wf["16"]["inputs"]["filename_prefix"] = f"pipeline_v7/{output_name}"
    
    # 关键参数
    wf["5"]["inputs"]["shift"] = shift
    wf["6"]["inputs"]["shift"] = shift
    split = steps // 2
    wf["12"]["inputs"]["steps"] = steps
    wf["12"]["inputs"]["cfg"] = cfg
    wf["12"]["inputs"]["end_at_step"] = split
    wf["13"]["inputs"]["steps"] = steps
    wf["13"]["inputs"]["cfg"] = cfg
    wf["13"]["inputs"]["start_at_step"] = split
    
    pid = queue_prompt(wf, f"wan_{output_name}")
    print(f"  Queued: {pid}")
    result = wait(pid, timeout=1800)
    if not result:
        print(f"  [ERR] Timeout")
        return None
    
    files = get_output_files(result)
    if files:
        src = files[0]
        dst = OUTPUT_DIR / f"{output_name}.mp4"
        shutil.copy2(src, dst)
        print(f"  [OK] {dst.name} ({dst.stat().st_size//1024}KB)")
        return str(dst)
    
    print(f"  [ERR] No output")
    return None


# ============================================================
# Main: 完整 Pipeline
# ============================================================
if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check ComfyUI
    try:
        r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        stats = json.loads(r.read())
        vram = stats['devices'][0]['vram_free'] / 1e9
        print(f"ComfyUI OK | VRAM: {vram:.1f}GB free")
    except:
        print("ComfyUI not available!")
        exit(1)
    
    # ---- 定义场景 ----
    FIRST_PROMPT = (
        "masterpiece, best quality, anime illustration, 1boy, young high school student, "
        "short messy black hair, bright eyes, gentle smile, "
        "wearing white short-sleeve school uniform shirt with dark blue necktie, "
        "standing at cherry blossom tree, spring afternoon, golden hour lighting, "
        "pink petals falling around him, one hand reaching up to catch a petal, "
        "detailed face, sharp eyes, soft skin, hair strands visible, "
        "school gate in background, depth of field, cinematic composition, "
        "vertical orientation 9:16"
    )
    
    LAST_PROMPT = (
        "masterpiece, best quality, anime illustration, 1boy, young high school student, "
        "short messy black hair, bright eyes, gentle smile, "
        "wearing white short-sleeve school uniform shirt with dark blue necktie, "
        "standing at cherry blossom tree, spring afternoon, golden hour lighting, "
        "pink petals falling around him, hand now holding a single cherry blossom petal, "
        "looking at petal in palm with soft wonder, "
        "detailed face, sharp eyes, soft skin, hair strands visible, "
        "school gate in background, depth of field, cinematic composition, "
        "vertical orientation 9:16"
    )
    
    MOTION_PROMPT = (
        "cinematic anime, young man slowly raises his hand and catches a falling "
        "cherry blossom petal in his palm, gentle spring breeze blowing, "
        "dozens of pink petals floating in golden sunlight, "
        "camera slowly zooms in on his face, warm afternoon light, "
        "smooth continuous motion, detailed face throughout, "
        "no scene cut, 5 second shot"
    )
    
    # ---- Step 1: 生成首帧 ----
    first_img = generate_flux_frame(
        prompt=FIRST_PROMPT,
        output_name="v7_first",
        width=480, height=832,
        steps=25, cfg=3.5, seed=42
    )
    if not first_img:
        print("首帧生成失败!")
        exit(1)
    
    # ---- Step 1b: 生成尾帧 ----
    last_img = generate_flux_frame(
        prompt=LAST_PROMPT,
        output_name="v7_last",
        width=480, height=832,
        steps=25, cfg=3.5, seed=43
    )
    if not last_img:
        print("尾帧生成失败!")
        exit(1)
    
    # ---- Step 2: 生成视频 ----
    video = generate_wan_video(
        first_img=first_img,
        last_img=last_img,
        motion_prompt=MOTION_PROMPT,
        output_name="v7_flux_shift12",
        width=480, height=832,
        steps=22, cfg=4.0, shift=12.0
    )
    if not video:
        print("视频生成失败!")
        exit(1)
    
    print(f"\n{'='*60}")
    print(f"PIPELINE V7 COMPLETE!")
    print(f"  首帧: {OUTPUT_DIR / 'v7_first.png'}")
    print(f"  尾帧: {OUTPUT_DIR / 'v7_last.png'}")
    print(f"  视频: {video}")
    print(f"  参数: Flux(25steps) → Wan I2V(22steps, shift=12, euler+simple)")
    print(f"{'='*60}")
