#!/usr/bin/env python3
"""
改进测试：大动作拆镜头策略
原版：1 个 5 秒镜头（跳起接花瓣）→ 6/10 穿帮
改进：3 个短镜头拆分，每个首尾帧姿态差异小
"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW_I2V = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test\improved_jump")

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

def generate_wan_video(first_img, last_img, motion_prompt, output_name,
                       width=480, height=832, steps=22, cfg=4.0, shift=12.0):
    print(f"  [Wan]  {output_name}...", end="", flush=True)
    with open(WORKFLOW_I2V, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)
    wf["9"]["inputs"]["image"] = first_img
    wf["10"]["inputs"]["image"] = last_img
    wf["7"]["inputs"]["text"] = motion_prompt
    wf["11"]["inputs"]["width"] = width
    wf["11"]["inputs"]["height"] = height
    wf["11"]["inputs"]["length"] = 81
    wf["16"]["inputs"]["filename_prefix"] = f"improved_jump/{output_name}"
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
# 人物基础描述（保持一致）
# ============================================================
CHAR = (
    "1boy, young high school student, age 17, short messy dark brown hair with side bangs, "
    "bright amber eyes, gentle expression, "
    "wearing white short-sleeve school uniform shirt with dark blue necktie, "
    "dark navy school trousers, white sneakers"
)
ENV = (
    "school courtyard with cherry blossom trees in full bloom, spring afternoon, "
    "golden hour warm sunlight, pink petals floating in air, "
    "school building in background, stone pathway, cinematic lighting"
)


# ============================================================
# 拆镜头策略：3 个短镜头
# ============================================================

SHOTS = [
    {
        "id": "seg1_prepare",
        "desc": "镜头1：准备起跳（蹲下蓄力）— 姿态变化小",
        "first_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"standing under cherry blossom tree in {ENV}, "
            "standing upright, looking up at falling petals, relaxed pose, "
            "detailed face, sharp eyes, vertical 9:16"
        ),
        "last_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"under cherry blossom tree in {ENV}, "
            "crouching slightly, knees bent, arms pulling back, about to jump, "
            "focused expression looking upward, "
            "detailed face, sharp eyes, vertical 9:16"
        ),
        "motion_prompt": (
            "cinematic anime, the young man slowly crouches down, bending his knees, "
            "pulling his arms back in preparation to jump, "
            "eyes fixed on a falling cherry blossom petal above, "
            "coiled energy, about to spring upward, "
            "camera holds steady at medium shot, golden sunlight, "
            "smooth controlled motion, consistent body, "
            "no scene cut, 5 second shot"
        ),
    },
    {
        "id": "seg2_jump",
        "desc": "镜头2：跳起+伸手（核心动作）— 始终在空中",
        "first_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"under cherry blossom tree in {ENV}, "
            "just launched off ground, feet leaving the stone path, "
            "body extending upward, arms starting to reach up, "
            "determined expression, looking up, "
            "detailed face, sharp eyes, vertical 9:16"
        ),
        "last_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"under cherry blossom tree in {ENV}, "
            "at apex of jump, fully airborne, both arms stretched high, "
            "fingers reaching toward a single pink petal, "
            "happy excited expression, hair floating upward, "
            "shirt and tie fluttering from motion, "
            "detailed face, sharp eyes, vertical 9:16"
        ),
        "motion_prompt": (
            "cinematic anime, the young man jumps upward energetically, "
            "rising into the air, both arms reaching higher and higher, "
            "fingers stretching toward a falling cherry blossom petal, "
            "at the apex his hands are near the petal, "
            "hair floats upward, tie flutters, shirt ripples, "
            "petals scatter around him from the motion, "
            "camera holds steady showing full body in the air, "
            "smooth upward motion, consistent proportions, "
            "no extra limbs, no deformation, "
            "no scene cut, 5 second shot"
        ),
    },
    {
        "id": "seg3_catch_land",
        "desc": "镜头3：接住花瓣+落地（收尾）— 手部特写减少变形",
        "first_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"under cherry blossom tree in {ENV}, "
            "at apex of jump, one hand catching a pink cherry blossom petal between fingers, "
            "triumphant smile, still airborne, starting to descend, "
            "detailed face, sharp eyes, close-up of hand with petal, "
            "vertical 9:16"
        ),
        "last_prompt": (
            f"masterpiece, best quality, anime illustration, {CHAR}, "
            f"under cherry blossom tree in {ENV}, "
            "just landed on ground, one foot touching down, knees slightly bent to absorb impact, "
            "holding the caught petal gently in one palm, looking at it with wonder, "
            "detailed face, soft smile, vertical 9:16"
        ),
        "motion_prompt": (
            "cinematic anime, the young man catches a cherry blossom petal in his hand "
            "and begins descending back to the ground, "
            "feet touch down gently, knees bend to absorb the landing, "
            "he brings the petal close to his face and looks at it with soft wonder, "
            "gentle smile, warm golden sunlight on his face, "
            "petals still floating around him, "
            "camera slowly zooms in on his face and the petal in his hand, "
            "smooth landing motion, consistent character, "
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
    print(f"改进测试：大动作拆镜头（3 段式跳起接花瓣）")
    print(f"{'='*60}")

    results = []
    for shot in SHOTS:
        print(f"\n--- {shot['id']}: {shot['desc']} ---")

        first = generate_flux_frame(shot["first_prompt"], f"{shot['id']}_first", seed=42)
        if not first:
            results.append({"id": shot["id"], "status": "flux_first_failed"})
            continue

        last = generate_flux_frame(shot["last_prompt"], f"{shot['id']}_last", seed=43)
        if not last:
            results.append({"id": shot["id"], "status": "flux_last_failed"})
            continue

        video = generate_wan_video(first, last, shot["motion_prompt"], shot["id"], shift=12.0)
        if video:
            results.append({"id": shot["id"], "status": "ok", "video": video})
        else:
            results.append({"id": shot["id"], "status": "wan_failed"})

    print(f"\n{'='*60}")
    print(f"拆镜头测试完成！结果在: {OUTPUT_DIR}")
    print(f"{'='*60}")
    for r in results:
        status = "[OK]" if r["status"] == "ok" else f"[{r['status']}]"
        print(f"  {status} {r['id']}")

    print(f"\n对比审查要点:")
    print(f"  seg1: 蹲下蓄力是否流畅，无变形")
    print(f"  seg2: 跳起时手脚是否正常（原版此处穿帮最严重）")
    print(f"  seg3: 接花瓣+落地，手部特写是否清晰")
