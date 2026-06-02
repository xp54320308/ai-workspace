"""
商业级短视频测试 - 完整流程 v2
Step 1: IP-Adapter Advanced + masks 生成高质量首帧
Step 2: Wan 2.2 I2V 转为15秒视频
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
COMFYUI_INPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

CKPT = "sd_xl_base_1.0.safetensors"
IP_MODEL = "ip-adapter-plus_sdxl_vit-h.safetensors"
CLIP_VISION = "ipadapter_sd15_model.safetensors"
PORTRAIT_A = "portrait_A.png"
PORTRAIT_B = "portrait_B.png"

WAN_HIGH = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
WAN_LOW = "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
WAN_VAE = "wan_2.1_vae.safetensors"
T5 = "umt5_xxl_fp16.safetensors"
WAN_CLIP_VISION = "clip_vision_h.safetensors"

PREFIX = "commercial"

def queue_prompt(w):
    data = json.dumps({"prompt": w, "client_id": "commercial"}).encode()
    req = urllib.request.Request(f"{COMFYUI}/prompt", data=data,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]

def wait(pid, timeout=900):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = json.loads(urllib.request.urlopen(f"{COMFYUI}/history/{pid}").read())
            if pid in r:
                return r[pid]
        except: pass
        time.sleep(5)
    return None

# ============================================================
# STEP 1: IP-Adapter + Mask 分区生成首帧
# ============================================================
print("=== STEP 1: 生成商业级首帧 ===")

prompt_a = "masterpiece, best quality, 1girl, anime style, silver hair, blue eyes, wearing elegant white blouse, sitting at cafe table, soft warm lighting, detailed face, looking at viewer, cozy cafe interior, bokeh background"
prompt_b = "masterpiece, best quality, 1girl, anime style, pink hair, green eyes, wearing stylish black leather jacket, confident pose, neon city lights, night urban background, reflections on wet street"
prompt_neg = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, blurry, deformed, watermark, signature"

ip_workflow = {
    # Loaders
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
    "7": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": CLIP_VISION}},
    "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": IP_MODEL}},
    "5": {"class_type": "LoadImage", "inputs": {"image": PORTRAIT_A}},
    "6": {"class_type": "LoadImage", "inputs": {"image": PORTRAIT_B}},

    # Prompts
    "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_a, "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_neg, "clip": ["1", 1]}},
    "8": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_b, "clip": ["1", 1]}},
    "24": {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["2", 0], "conditioning_2": ["8", 0]}},

    # Masks - left 45% and right 45%
    "40": {"class_type": "MaskRectArea", "inputs": {"x": 0, "y": 0, "width": 45, "height": 100, "blur_radius": 5}},
    "41": {"class_type": "MaskRectArea", "inputs": {"x": 55, "y": 0, "width": 45, "height": 100, "blur_radius": 5}},

    # IPAdapter #1 - left character
    "50": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["1", 0], "ipadapter": ["10", 0], "image": ["5", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["40", 0], "clip_vision": ["7", 0]
    }},
    # IPAdapter #2 - right character (chained)
    "51": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["50", 0], "ipadapter": ["10", 0], "image": ["6", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["41", 0], "clip_vision": ["7", 0]
    }},

    # Latent
    "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 576, "batch_size": 1}},

    # Sample
    "30": {"class_type": "KSampler", "inputs": {
        "model": ["51", 0], "positive": ["24", 0], "negative": ["3", 0],
        "latent_image": ["4", 0],
        "seed": 12345, "steps": 30, "cfg": 7.0,
        "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "denoise": 1.0
    }},
    "31": {"class_type": "VAEDecode", "inputs": {"samples": ["30", 0], "vae": ["1", 2]}},
    "32": {"class_type": "SaveImage", "inputs": {"images": ["31", 0], "filename_prefix": f"{PREFIX}_frame"}}
}

pid = queue_prompt(ip_workflow)
print(f"IP-Adapter queued: {pid}")
result = wait(pid)
if not result or pid not in result:
    print("IP-Adapter FAILED!")
    exit(1)

outputs = result[pid]["outputs"]
frame_file = None
for nid, out in outputs.items():
    if "images" in out:
        for img in out["images"]:
            frame_file = img["filename"]
            if "subfolder" in img and img["subfolder"]:
                frame_file = os.path.join(img["subfolder"], frame_file)

src = os.path.join(COMFYUI_OUTPUT, frame_file)
dst = os.path.join(COMFYUI_INPUT, f"{PREFIX}_frame.png")
shutil.copy2(src, dst)
ws_frame = os.path.join(OUTPUT_DIR, f"{PREFIX}_frame.png")
shutil.copy2(src, ws_frame)
print(f"首帧完成: {frame_file}")

# ============================================================
# STEP 2: Wan 2.2 I2V - 15秒视频
# ============================================================
print("\n=== STEP 2: Wan 2.2 I2V 生成15秒视频 ===")

WIDTH, HEIGHT = 832, 480
FRAMES = 121  # 15.1s @ 8fps
STEPS = 20
CFG = 5.0
SHIFT = 8.0
SPLIT = 10
SEED = 42

vid_workflow = {
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": T5, "precision": "bf16"
    }},
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "cinematic anime scene, two girls in urban setting, soft warm lighting, camera slowly pans right, golden hour light, cherry blossoms falling, detailed anime style, commercial quality, smooth motion, depth of field",
        "negative_prompt": "blurry, low quality, distorted, artifacts, static, no motion",
        "t5": ["11", 0]
    }},
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": WAN_HIGH, "base_precision": "bf16",
        "quantization": "disabled", "load_device": "offload_device"
    }},
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": WAN_LOW, "base_precision": "bf16",
        "quantization": "disabled", "load_device": "offload_device"
    }},
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": WAN_VAE, "precision": "bf16"
    }},
    "66": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": WAN_CLIP_VISION}},
    "67": {"class_type": "LoadImage", "inputs": {"image": f"{PREFIX}_frame.png"}},
    "68": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["66", 0], "image": ["67", 0], "crop": "center"
    }},
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": WIDTH, "height": HEIGHT, "num_frames": FRAMES,
        "noise_aug_strength": 0.0, "start_latent_strength": 1.0,
        "end_latent_strength": 1.0, "force_offload": True,
        "vae": ["38", 0], "clip_embeds": ["68", 0],
        "start_image": ["67", 0],
        "fun_or_fl2v_model": False, "tiled_vae": False
    }},
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": STEPS, "cfg": CFG, "shift": SHIFT,
        "seed": SEED, "scheduler": "dpm++_sde",
        "riflex_freq_index": 0, "force_offload": True,
        "start_step": 0, "end_step": SPLIT
    }},
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": STEPS, "cfg": CFG, "shift": SHIFT,
        "seed": SEED, "scheduler": "dpm++_sde",
        "riflex_freq_index": 0, "force_offload": True,
        "samples": ["27", 0], "start_step": SPLIT, "end_step": -1
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "samples": ["90", 0], "vae": ["38", 0], "enable_vae_tiling": True
    }},
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "fps": 8, "loop_count": 0,
        "filename_prefix": f"{PREFIX}_video",
        "format": "video/h264-mp4", "save_output": True
    }}
}

pid2 = queue_prompt(vid_workflow)
print(f"Wan I2V queued: {pid2}")
result2 = wait(pid2, timeout=900)
if not result2 or pid2 not in result2:
    print("Wan I2V FAILED!")
    exit(1)

outputs2 = result2[pid2]["outputs"]
video_file = None
for nid, out in outputs2.items():
    if "gifs" in out:
        for v in out["gifs"]:
            video_file = v["filename"]
            if "subfolder" in v and v["subfolder"]:
                video_file = os.path.join(v["subfolder"], video_file)

src2 = os.path.join(COMFYUI_OUTPUT, video_file)
dst2 = os.path.join(OUTPUT_DIR, f"{PREFIX}_video.mp4")
shutil.copy2(src2, dst2)
print(f"\n=== DONE! ===")
print(f"首帧: {ws_frame}")
print(f"视频: {dst2}")
print(f"时长: ~15s (121帧 @ 8fps)")
