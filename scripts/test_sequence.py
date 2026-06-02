#!/usr/bin/env python3
"""
V7 衔接片段测试：3 镜头连续叙事
关键：每个镜头的尾帧 = 下一个镜头的首帧参考（保持人物一致性）
故事：少年在樱花树下 → 接花瓣 → 看花瓣微笑
"""
import json, os, time, urllib.request, urllib.parse, uuid, shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")
WORKFLOW_I2V = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
OUTPUT_DIR = Path(r"G:\manga_drama_project\test\sequence")

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
    wf["16"]["inputs"]["filename_prefix"] = f"sequence/{output_name}"
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
# 人物+环境固定描述（保证一致性）
# ============================================================
CHAR = (
    "1boy, young high school student, age 17, short messy dark brown hair with ahoge cowlick, "
    "bright amber eyes, soft blush on cheeks, gentle smile, "
    "wearing white short-sleeve school uniform shirt with dark blue necktie, "
    "dark navy school trousers, black belt with gold buckle, white sneakers"
)

ENV = (
    "school courtyard with cherry blossom trees in full bloom, spring late afternoon, "
    "golden hour warm sunlight casting long shadows, pink petals floating in air, "
    "stone pathway, school building with large windows in background, "
    "clear blue sky, cinematic anime lighting"
)

STYLE = "masterpiece, best quality, anime illustration, detailed face, sharp eyes, hair strands visible, vertical 9:16"


# ============================================================
# 3 镜头连续叙事
# ============================================================

SHOTS = [
    {
        "id": "s1_looking_up",
        "desc": "镜头1：少年抬头看樱花（建立场景+角色）",
        "first_prompt": f"{STYLE}, {CHAR}, standing at school gate under cherry blossom tree, {ENV}, looking slightly upward with wonder at falling petals, one hand in pocket, relaxed pose, side profile",
        "last_prompt": f"{STYLE}, {CHAR}, standing at school gate under cherry blossom tree, {ENV}, now looking directly upward with both eyes wide, mouth slightly open in awe, petals falling around his face, arms starting to lift slightly",
        "motion_prompt": (
            "cinematic anime, the young man slowly tilts his head upward to look at cherry blossoms, "
            "eyes widen with wonder, mouth opens slightly in awe, "
            "pink petals drift past his face, golden sunlight illuminates his features, "
            "one arm starts to lift slightly as if wanting to reach for a petal, "
            "camera slowly tilts up with him, smooth motion, "
            "consistent face and identity, no scene cut, 5 second shot"
        ),
    },
    {
        "id": "s2_reaching",
        "desc": "镜头2：伸手接花瓣（核心动作，中等幅度）",
        "first_prompt": f"{STYLE}, {CHAR}, standing under cherry blossom tree, {ENV}, looking upward with right arm raised, hand open, reaching toward a falling pink petal, determined gentle expression, petals everywhere",
        "last_prompt": f"{STYLE}, {CHAR}, standing under cherry blossom tree, {ENV}, right hand now closed gently around a single cherry blossom petal, bringing it down toward chest level, triumphant soft smile, eyes looking at the petal in hand",
        "motion_prompt": (
            "cinematic anime, the young man reaches his right hand up toward a falling cherry blossom petal, "
            "fingers spread, then gently closes his hand around the petal, "
            "brings his hand down slowly to chest level, "
            "a soft triumphant smile appears on his face, eyes focused on the petal in his palm, "
            "cherry blossom petals continue falling around him, golden sunlight, "
            "camera follows the hand motion smoothly, "
            "consistent face, consistent clothing, smooth motion, "
            "no scene cut, 5 second shot"
        ),
    },
    {
        "id": "s3_admire",
        "desc": "镜头3：低头看花瓣微笑（收尾+情感）",
        "first_prompt": f"{STYLE}, {CHAR}, standing under cherry blossom tree, {ENV}, holding a single pink cherry blossom petal in right palm at chest level, looking down at the petal, soft warm smile, gentle expression",
        "last_prompt": f"{STYLE}, {CHAR}, standing under cherry blossom tree, {ENV}, still holding the petal, now looking up from the petal with a peaceful content smile, eyes gentle and warm, petals still falling around him, sunset light on face",
        "motion_prompt": (
            "cinematic anime, the young man looks down at the cherry blossom petal in his palm, "
            "then slowly lifts his gaze from the petal, "
            "a peaceful content smile spreads across his face, "
            "he looks up into the falling petals with warm gentle eyes, "
            "golden sunset light catches his face, petals drift around him, "
            "camera slowly zooms in on his smiling face, "
            "consistent identity, smooth emotion transition, "
            "no scene cut, 5 second shot"
        ),
    },
]


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

    print(f"\n{'='*60}")
    print(f"V7 衔接片段：3 镜头连续叙事")
    print(f"  少年看樱花 → 接花瓣 → 微笑")
    print(f"{'='*60}")

    results = []
    prev_last_img = None

    for i, shot in enumerate(SHOTS):
        print(f"\n--- 镜头 {i+1}: {shot['desc']} ---")

        # 首帧：如果已有上一个镜头的尾帧，复用它
        if prev_last_img:
            first_img = prev_last_img
            print(f"  [复用] 首帧 = 上一镜头尾帧: {first_img}")
        else:
            first_img = generate_flux_frame(shot["first_prompt"], f"{shot['id']}_first", seed=42)
            if not first_img:
                results.append({"id": shot["id"], "status": "flux_first_failed"})
                continue

        # 尾帧：用 Flux 生成（保持人物一致性）
        last_img = generate_flux_frame(shot["last_prompt"], f"{shot['id']}_last", seed=43)
        if not last_img:
            results.append({"id": shot["id"], "status": "flux_last_failed"})
            continue

        # Wan I2V 视频
        video = generate_wan_video(first_img, last_img, shot["motion_prompt"], shot["id"], shift=12.0)
        if video:
            results.append({"id": shot["id"], "status": "ok", "video": video})
            prev_last_img = last_img  # 尾帧传给下一个镜头
        else:
            results.append({"id": shot["id"], "status": "wan_failed"})

    # 汇总
    print(f"\n{'='*60}")
    print(f"衔接片段生成完成！结果在: {OUTPUT_DIR}")
    print(f"{'='*60}")
    for r in results:
        status = "[OK]" if r["status"] == "ok" else f"[{r['status']}]"
        print(f"  {status} {r['id']}")

    print(f"\n审查要点:")
    print(f"  1. 镜头之间人物是否一致（脸/服装不漂移）")
    print(f"  2. 环境是否连贯（樱花/光线/背景）")
    print(f"  3. 情绪是否流畅过渡（好奇→惊喜→满足）")
    print(f"\n用 ffmpeg 拼接:")
    print(f'  ffmpeg -f concat -safe 0 -i list.txt -c copy sequence_merged.mp4')
