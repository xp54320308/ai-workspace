#!/usr/bin/env python3
"""
连贯性测试：人物一致性 + 环境稳定性 + 大动作穿帮
三个场景，逐步加大难度
"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW_I2V = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test\coherence")

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
    """Flux 生成高质量帧"""
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
    """Wan I2V 生成视频"""
    print(f"  [Wan]  {output_name}...", end="", flush=True)
    with open(WORKFLOW_I2V, "r", encoding="utf-8-sig") as f:
        wf = json.load(f)
    wf["9"]["inputs"]["image"] = first_img
    wf["10"]["inputs"]["image"] = last_img
    wf["7"]["inputs"]["text"] = motion_prompt
    wf["11"]["inputs"]["width"] = width
    wf["11"]["inputs"]["height"] = height
    wf["11"]["inputs"]["length"] = 81
    wf["16"]["inputs"]["filename_prefix"] = f"coherence/{output_name}"
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
CHAR_A = (
    "1boy, young high school student, age 17, short messy black hair with side bangs, "
    "bright dark brown eyes, gentle expression, "
    "wearing white short-sleeve school uniform shirt with dark blue necktie, "
    "dark school trousers, white sneakers"
)

ENV_SCHOOL = (
    "school courtyard with cherry blossom trees in full bloom, spring afternoon, "
    "golden hour warm sunlight, pink petals floating in air, "
    "school building with large windows in background, stone pathway, "
    "depth of field, cinematic lighting"
)


# ============================================================
# 场景 A：微动作 — 人物一致性基准
# 测试：脸部/服装是否在整段视频中保持一致
# ============================================================
TEST_A = {
    "name": "A_gentle_face_consistency",
    "desc": "微动作：角色缓慢转头看镜头（测试脸部一致性）",
    "first_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"standing in {ENV_SCHOOL}, "
        "looking slightly to the left, side profile, "
        "detailed face, sharp eyes, hair strands visible, "
        "vertical 9:16 composition"
    ),
    "last_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"standing in {ENV_SCHOOL}, "
        "now turned head to face camera directly, front view, "
        "detailed face, sharp eyes, same hair style, same uniform, "
        "vertical 9:16 composition"
    ),
    "motion_prompt": (
        "cinematic anime, the young man slowly turns his head from side profile "
        "to face the camera directly, gentle smile appears, "
        "cherry blossom petals drift past his face, "
        "hair moves slightly with the turn, "
        "camera holds steady, soft golden lighting, "
        "smooth continuous motion, consistent face and identity throughout, "
        "no scene cut, 5 second shot"
    ),
    "shift": 12.0,
}


# ============================================================
# 场景 B：中等动作 — 环境稳定性
# 测试：背景是否在运动中保持稳定，不扭曲变形
# ============================================================
TEST_B = {
    "name": "B_walk_env_stability",
    "desc": "中等动作：角色行走+镜头跟随（测试环境稳定性）",
    "first_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"standing at start of stone pathway in {ENV_SCHOOL}, "
        "standing still, about to walk, relaxed pose, "
        "detailed face, sharp eyes, "
        "vertical 9:16 composition"
    ),
    "last_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"walking along stone pathway in {ENV_SCHOOL}, "
        "mid-stride, one foot forward, arms swinging naturally, "
        "detailed face from slightly different angle, same uniform, "
        "vertical 9:16 composition"
    ),
    "motion_prompt": (
        "cinematic anime, the young man starts walking forward along a stone pathway, "
        "natural walking motion, arms swinging, footsteps visible, "
        "camera follows him from the side, slight camera pan right, "
        "cherry blossom trees pass by in background, petals falling, "
        "consistent environment, background stays stable and coherent, "
        "same school building and trees throughout, "
        "smooth continuous motion, no scene cut, 5 second shot"
    ),
    "shift": 12.0,
}


# ============================================================
# 场景 C：大动作 — 穿帮压力测试
# 测试：大幅度动作（跳起接花瓣）是否导致变形/穿帮
# ============================================================
TEST_C = {
    "name": "C_jump_action_stress",
    "desc": "大动作：跳起接花瓣（压力测试，最容易穿帮）",
    "first_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"standing under cherry blossom tree in {ENV_SCHOOL}, "
        "standing on ground, looking up at falling petals, "
        "about to jump, knees slightly bent, "
        "detailed face, sharp eyes, "
        "vertical 9:16 composition"
    ),
    "last_prompt": (
        f"masterpiece, best quality, anime illustration, {CHAR_A}, "
        f"under cherry blossom tree in {ENV_SCHOOL}, "
        "jumping up in the air, feet off ground, reaching both hands up high, "
        "catching a cherry blossom petal between fingers, "
        "happy excited expression, hair flying up with motion, "
        "shirt and tie fluttering, dynamic pose, "
        "vertical 9:16 composition"
    ),
    "motion_prompt": (
        "cinematic anime, the young man jumps up energetically to catch a falling "
        "cherry blossom petal, big dynamic jump with both arms reaching high, "
        "feet leave the ground, body stretches upward, "
        "hair flies up with the motion, shirt and tie flutter, "
        "petals scatter around him from the movement, "
        "then starts descending back down, "
        "camera holds steady showing full body, "
        "smooth continuous motion, consistent body proportions, "
        "no deformation, no extra limbs, no scene cut, 5 second shot"
    ),
    "shift": 12.0,
}


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        r = urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5)
        stats = json.loads(r.read())
        print(f"ComfyUI OK | VRAM: {stats['devices'][0]['vram_free']/1e9:.1f}GB free")
    except:
        print("ComfyUI not available!")
        exit(1)

    tests = [TEST_A, TEST_B, TEST_C]
    results = []

    for test in tests:
        print(f"\n{'='*60}")
        print(f"场景: {test['name']}")
        print(f"描述: {test['desc']}")
        print(f"{'='*60}")

        # Flux 首帧
        first = generate_flux_frame(test["first_prompt"], f"{test['name']}_first", seed=42)
        if not first:
            print(f"  [SKIP] 首帧生成失败")
            results.append({"name": test["name"], "status": "flux_first_failed"})
            continue

        # Flux 尾帧
        last = generate_flux_frame(test["last_prompt"], f"{test['name']}_last", seed=43)
        if not last:
            print(f"  [SKIP] 尾帧生成失败")
            results.append({"name": test["name"], "status": "flux_last_failed"})
            continue

        # Wan I2V
        video = generate_wan_video(first, last, test["motion_prompt"],
                                    test["name"], shift=test["shift"])
        if video:
            results.append({"name": test["name"], "status": "ok", "video": video})
        else:
            results.append({"name": test["name"], "status": "wan_failed"})

    # 汇总
    print(f"\n{'='*60}")
    print(f"连贯性测试完成！结果在: {OUTPUT_DIR}")
    print(f"{'='*60}")
    for r in results:
        status = "[OK]" if r["status"] == "ok" else f"[{r['status']}]"
        print(f"  {status} {r['name']}")
    print(f"\n请用 ffplay 或播放器审查:")
    print(f"  A: 脸部一致性（转头时脸是否变形）")
    print(f"  B: 环境稳定性（背景是否扭曲/跳变）")
    print(f"  C: 大动作穿帮（跳起时是否多手多脚/变形）")
