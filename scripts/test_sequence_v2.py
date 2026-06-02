#!/usr/bin/env python3
"""
V7 改进版：更写实、更稳、更一致
修复：
1. 去掉飘逸感 → 减少花瓣描述，加 weight/grounding 负面提示
2. 人物一致性 → 统一 Flux seed 基础 + 更精确的角色描述
3. 场景流畅 → 降低 shift=8，减少过度运动
"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW_I2V = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test\sequence_v2")

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

def generate_flux_frame(prompt, output_name, width=480, height=832, steps=25, cfg=3.5, seed=42):
    print(f"  [Flux] {output_name}...", end="", flush=True)
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
    result = wait(pid, timeout=600)
    if not result:
        print(" ERR")
        return None
    files = get_output_files(result)
    if files:
        src = files[0]
        shutil.copy2(src, COMFYUI_INPUT / f"{output_name}.png")
        dst = OUTPUT_DIR / f"{output_name}.png"
        shutil.copy2(src, dst)
        print(f" OK ({dst.stat().st_size//1024}KB)")
        return f"{output_name}.png"
    print(" ERR")
    return None

def generate_wan_video(first_img, last_img, motion_prompt, negative_prompt, output_name,
                       width=480, height=832, steps=22, cfg=4.0, shift=8.0):
    print(f"  [Wan]  {output_name} (shift={shift})...", end="", flush=True)
    with open(WORKFLOW_I2V, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)
    wf["9"]["inputs"]["image"] = first_img
    wf["10"]["inputs"]["image"] = last_img
    wf["7"]["inputs"]["text"] = motion_prompt
    # 覆盖负面提示
    if "8" in wf and "inputs" in wf["8"]:
        wf["8"]["inputs"]["text"] = negative_prompt
    wf["11"]["inputs"]["width"] = width
    wf["11"]["inputs"]["height"] = height
    wf["11"]["inputs"]["length"] = 81
    wf["16"]["inputs"]["filename_prefix"] = f"sequence_v2/{output_name}"
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
    result = wait(pid, timeout=1800)
    if not result:
        print(" ERR")
        return None
    files = get_output_files(result)
    if files:
        src = files[0]
        dst = OUTPUT_DIR / f"{output_name}.mp4"
        shutil.copy2(src, dst)
        print(f" OK ({dst.stat().st_size//1024}KB)")
        return str(dst)
    print(" ERR")
    return None


# ============================================================
# 统一角色描述（精确到每个细节，保证一致性）
# ============================================================
CHAR_EXACT = (
    "1boy, age 17, short messy dark brown hair with one ahoge cowlick on top, "
    "large amber-orange eyes, small nose, soft pink blush on cheeks, "
    "white short-sleeve button-up school shirt, "
    "dark blue necktie with simple knot, "
    "dark navy trousers, black leather belt with rectangular gold buckle, "
    "white canvas sneakers with white laces, "
    "slim athletic build, average height"
)

ENV_EXACT = (
    "school courtyard, stone paved pathway, "
    "cherry blossom trees with pink flowers lining both sides, "
    "two-story school building with white walls and large windows in background, "
    "clear blue sky, late afternoon warm golden sunlight from the left, "
    "soft shadows on the ground"
)

# 更写实的负面提示（去飘逸感）
NEGATIVE = (
    "floaty, ethereal, dreamy, misty, foggy, soft focus, "
    "excessive petals, petal storm, too many petals, "
    "glowing, sparkling, magical particles, "
    "identity change, different person, face drift, "
    "deformed face, deformed hands, extra fingers, "
    "blurry, low quality, watermark, "
    "hard scene cut, different lighting, different time of day"
)

STYLE = "masterpiece, best quality, anime illustration, detailed, sharp focus, cinematic"


# ============================================================
# 3 镜头：更写实的叙事
# ============================================================

SHOTS = [
    {
        "id": "v2s1_stand",
        "desc": "镜头1：少年站在樱花树下（静态建立）",
        "first_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing still on stone pathway, {ENV_EXACT}, "
            "looking forward with a calm relaxed expression, both arms at sides, "
            "a few cherry blossom petals on the ground, "
            "stable composition, grounded pose, weight on both feet"
        ),
        "last_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing still on stone pathway, {ENV_EXACT}, "
            "now tilting head slightly upward, eyes looking up at the tree canopy, "
            "slight smile of wonder, still grounded, weight on both feet, "
            "one or two petals falling near his shoulder"
        ),
        "motion_prompt": (
            "cinematic anime, a young man stands still on a stone path, "
            "slowly tilts his head upward to look at cherry blossom tree, "
            "a calm peaceful expression, slight smile, "
            "a couple of petals drift down past his shoulder, "
            "he is firmly grounded, solid stance, no floating, "
            "camera holds steady at medium shot, "
            "natural afternoon lighting, consistent character, "
            "no scene cut, 5 second shot"
        ),
    },
    {
        "id": "v2s2_reach",
        "desc": "镜头2：伸手接一片花瓣（小幅度动作）",
        "first_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing on stone pathway, {ENV_EXACT}, "
            "looking upward with right arm slowly raising, hand open palm up, "
            "following a single falling petal with his eyes, "
            "grounded stance, left arm at side"
        ),
        "last_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing on stone pathway, {ENV_EXACT}, "
            "right hand now at chest height, fingers gently closed around one pink petal, "
            "looking down at the petal in his palm with a soft smile, "
            "grounded stance, left arm at side"
        ),
        "motion_prompt": (
            "cinematic anime, a young man slowly raises his right hand "
            "to catch a single falling cherry blossom petal, "
            "his eyes follow the petal as it drifts down, "
            "his fingers gently close around it, "
            "he brings his hand to chest height and looks at the petal, "
            "a soft smile appears, "
            "firmly grounded, no floating, natural arm motion, "
            "camera follows hand movement smoothly, "
            "consistent face and body, "
            "no scene cut, 5 second shot"
        ),
    },
    {
        "id": "v2s3_smile",
        "desc": "镜头3：看着花瓣微笑（情感收尾）",
        "first_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing on stone pathway, {ENV_EXACT}, "
            "looking down at a cherry blossom petal held in right palm, "
            "soft gentle smile, peaceful expression, both feet on ground"
        ),
        "last_prompt": (
            f"{STYLE}, {CHAR_EXACT}, standing on stone pathway, {ENV_EXACT}, "
            "now looking up from the petal, warm content smile, "
            "eyes gentle and happy, facing slightly toward camera, "
            "still holding the petal loosely in right hand, grounded"
        ),
        "motion_prompt": (
            "cinematic anime, a young man looks down at a cherry blossom petal in his hand, "
            "then slowly lifts his head to look forward, "
            "a warm content smile grows on his face, "
            "his eyes are gentle and happy, "
            "he stands firmly on the ground, relaxed posture, "
            "camera slowly moves closer to his face, "
            "natural lighting, consistent identity, "
            "no scene cut, 5 second shot"
        ),
    },
]


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        stats = json.loads(r.read())
        print(f"ComfyUI OK | VRAM: {stats['devices'][0]['vram_free']/1e9:.1f}GB free")
    except:
        print("ComfyUI not available!")
        exit(1)

    print(f"\n{'='*60}")
    print(f"V7 改进版：更写实、更稳、更一致")
    print(f"  shift=8 (原12), 负面提示去飘逸, 精确角色描述")
    print(f"{'='*60}")

    results = []
    prev_last_img = None

    for i, shot in enumerate(SHOTS):
        print(f"\n--- 镜头 {i+1}: {shot['desc']} ---")

        if prev_last_img:
            first_img = prev_last_img
            print(f"  [复用] 首帧 = 上一镜头尾帧: {first_img}")
        else:
            first_img = generate_flux_frame(shot["first_prompt"], f"{shot['id']}_first", seed=100)
            if not first_img:
                results.append({"id": shot["id"], "status": "flux_first_failed"})
                continue

        last_img = generate_flux_frame(shot["last_prompt"], f"{shot['id']}_last", seed=101)
        if not last_img:
            results.append({"id": shot["id"], "status": "flux_last_failed"})
            continue

        video = generate_wan_video(
            first_img, last_img,
            shot["motion_prompt"], NEGATIVE,
            shot["id"], shift=8.0
        )
        if video:
            results.append({"id": shot["id"], "status": "ok", "video": video})
            prev_last_img = last_img
        else:
            results.append({"id": shot["id"], "status": "wan_failed"})

    # 合并
    import subprocess
    ffmpeg = r"F:\Comfyui\ComfyUI-aki-v3\python\ffmpeg.exe"
    list_file = OUTPUT_DIR / "list.txt"
    with open(list_file, "w") as f:
        for r in results:
            if r["status"] == "ok":
                f.write(f"file '{Path(r['video']).name}'\n")

    merged = OUTPUT_DIR / "merged_v2.mp4"
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", str(list_file), "-c", "copy", str(merged)],
                   capture_output=True)

    print(f"\n{'='*60}")
    print(f"V2 完成！结果在: {OUTPUT_DIR}")
    print(f"{'='*60}")
    for r in results:
        status = "[OK]" if r["status"] == "ok" else f"[{r['status']}]"
        print(f"  {status} {r['id']}")
    if merged.exists():
        print(f"\n  合并: {merged.name} ({merged.stat().st_size//1024}KB)")
    print(f"\n改进点:")
    print(f"  1. shift=8 (原12) — 减少过度运动/飘逸感")
    print(f"  2. 负面提示 — 禁止floaty/ethereal/dreamy/excessive petals")
    print(f"  3. 精确角色描述 — 固定每个细节")
    print(f"  4. 更写实的prompt — grounded/weight/firm stance")
