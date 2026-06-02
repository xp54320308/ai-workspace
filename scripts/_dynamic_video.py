"""
动感短视频 - 更多动作元素
Step 1: 生成动感首帧
Step 2: 强调动作的 I2V
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
COMFYUI_INPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

def queue_prompt(w, cid="dynamic"):
    data = json.dumps({"prompt": w, "client_id": cid}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]

def wait(pid, timeout=1200):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
            if pid in r and r[pid].get("status", {}).get("completed"):
                return r[pid]
        except: pass
        time.sleep(10)
    return None

# ============================================================
# STEP 1: 动感首帧 - IP-Adapter 双角色
# ============================================================
print("=== STEP 1: 生成动感首帧 ===")

# 动感场景：两个角色在樱花街道上奔跑/战斗
prompt_a = "masterpiece, best quality, 1girl, anime style, silver hair flowing in wind, blue eyes, wearing white dress with ribbons, dynamic running pose, cherry blossom petals flying, motion blur, action scene, cinematic angle"
prompt_b = "masterpiece, best quality, 1girl, anime style, pink hair, green eyes, wearing black battle outfit, jumping pose mid-air, energy aura, dynamic action, wind blowing hair, dramatic lighting"
prompt_neg = "lowres, bad anatomy, bad hands, text, error, missing fingers, cropped, worst quality, low quality, blurry, deformed, watermark, static, stiff pose"

ip_workflow = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
    "7": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "ipadapter_sd15_model.safetensors"}},
    "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}},
    "5": {"class_type": "LoadImage", "inputs": {"image": "portrait_A.png"}},
    "6": {"class_type": "LoadImage", "inputs": {"image": "portrait_B.png"}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_a, "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_neg, "clip": ["1", 1]}},
    "8": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_b, "clip": ["1", 1]}},
    "24": {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["2", 0], "conditioning_2": ["8", 0]}},
    "40": {"class_type": "MaskRectArea", "inputs": {"x": 0, "y": 0, "width": 45, "height": 100, "blur_radius": 5}},
    "41": {"class_type": "MaskRectArea", "inputs": {"x": 55, "y": 0, "width": 45, "height": 100, "blur_radius": 5}},
    "50": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["1", 0], "ipadapter": ["10", 0], "image": ["5", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["40", 0], "clip_vision": ["7", 0]
    }},
    "51": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["50", 0], "ipadapter": ["10", 0], "image": ["6", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["41", 0], "clip_vision": ["7", 0]
    }},
    "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 576, "batch_size": 1}},
    "30": {"class_type": "KSampler", "inputs": {
        "model": ["51", 0], "positive": ["24", 0], "negative": ["3", 0],
        "latent_image": ["4", 0],
        "seed": 99999, "steps": 30, "cfg": 7.0,
        "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "denoise": 1.0
    }},
    "31": {"class_type": "VAEDecode", "inputs": {"samples": ["30", 0], "vae": ["1", 2]}},
    "32": {"class_type": "SaveImage", "inputs": {"images": ["31", 0], "filename_prefix": "dynamic_frame"}}
}

pid1 = queue_prompt(ip_workflow, "dynamic1")
print(f"IP-Adapter queued: {pid1}")
result1 = wait(pid1)
if not result1 or pid1 not in result1:
    print("FAILED!")
    exit(1)

frame_file = None
for nid, out in result1[pid1]["outputs"].items():
    if "images" in out:
        for img in out["images"]:
            frame_file = img["filename"]
            if img.get("subfolder"):
                frame_file = os.path.join(img["subfolder"], frame_file)

src = os.path.join(COMFYUI_OUTPUT, frame_file)
shutil.copy2(src, os.path.join(COMFYUI_INPUT, "dynamic_frame.png"))
shutil.copy2(src, os.path.join(OUTPUT_DIR, "dynamic_frame.png"))
print(f"首帧: {frame_file}")

# ============================================================
# STEP 2: Wan I2V - 强调动作
# ============================================================
print("\n=== STEP 2: 动感视频生成 ===")

# 关键改动：
# 1. start_latent_strength=0.85 (降低→更多运动自由度)
# 2. prompt 强调动作和运动
# 3. steps=25 (更多步数=更好质量)
# 4. cfg=5.5

vid_workflow = {
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
    }},
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "dynamic action scene, two anime girls running through cherry blossom street, hair flowing wildly in wind, petals swirling around them, fast camera movement following characters, dramatic perspective shifts, energetic motion, speed lines, cinematic anime, vibrant colors, intense action",
        "negative_prompt": "static, no motion, slow, stiff, boring, still frame, low quality, blurry, artifacts",
        "t5": ["11", 0]
    }},
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
    }},
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
    }},
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan_2.1_vae.safetensors", "precision": "bf16"
    }},
    "66": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "67": {"class_type": "LoadImage", "inputs": {"image": "dynamic_frame.png"}},
    "68": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["66", 0], "image_1": ["67", 0],
        "strength_1": 1.0, "strength_2": 1.0,
        "crop": "center", "combine_embeds": "concat", "force_offload": True
    }},
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": 832, "height": 480, "num_frames": 121,
        "noise_aug_strength": 0.02, "start_latent_strength": 0.85,
        "end_latent_strength": 1.0, "force_offload": True,
        "vae": ["38", 0], "clip_embeds": ["68", 0], "start_image": ["67", 0],
        "fun_or_fl2v_model": False, "tiled_vae": False
    }},
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 25, "cfg": 5.5, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "start_step": 0, "end_step": 12
    }},
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 25, "cfg": 5.5, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "samples": ["27", 0], "start_step": 12, "end_step": -1
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "samples": ["90", 0], "vae": ["38", 0],
        "enable_vae_tiling": True,
        "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128
    }},
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": 8.0, "loop_count": 0,
        "filename_prefix": "dynamic_video",
        "format": "video/h264-mp4", "pingpong": False, "save_output": True
    }}
}

pid2 = queue_prompt(vid_workflow, "dynamic2")
print(f"Wan I2V queued: {pid2}")
result2 = wait(pid2, timeout=1200)
if not result2 or pid2 not in result2:
    print("FAILED!")
    exit(1)

video_file = None
for nid, out in result2[pid2]["outputs"].items():
    if "gifs" in out:
        for v in out["gifs"]:
            video_file = v["filename"]
            if v.get("subfolder"):
                video_file = os.path.join(v["subfolder"], video_file)

src2 = os.path.join(COMFYUI_OUTPUT, video_file)
dst2 = os.path.join(OUTPUT_DIR, "dynamic_video.mp4")
shutil.copy2(src2, dst2)
print(f"\n=== DONE! ===")
print(f"视频: {dst2}")
print(f"Size: {os.path.getsize(dst2) / 1024 / 1024:.1f} MB")
