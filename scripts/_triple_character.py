"""
3+ 角色 IP-Adapter + Wan Video
3个角色，扩展区域 mask
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
COMFYUI_INPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

def queue_prompt(w, cid="multi3"):
    data = json.dumps({"prompt": w, "client_id": cid}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]

def wait(pid, timeout=1800):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
            if pid in r:
                status = r[pid].get("status", {})
                if status.get("completed") or status.get("status_str") == "error":
                    return r[pid]
        except: pass
        time.sleep(15)
    return None

# ============================================================
# STEP 1: Generate 3 portraits (if not exist)
# ============================================================
print("=== STEP 1: 生成3个角色头像 ===")

# Character C prompt
char_c_prompt = "masterpiece, best quality, 1girl, anime style, long purple hair, golden eyes, wearing red kimono with gold patterns, elegant pose, cherry blossom background, detailed face, beautiful lighting"
char_neg = "lowres, bad anatomy, bad hands, text, error, missing fingers, cropped, worst quality, low quality, blurry, deformed, watermark"

# Generate 3 portraits: A (silver/blue), B (pink/green), C (purple/gold)
portraits = {
    "A": {"prompt": "masterpiece, best quality, 1girl, anime style, silver hair, blue eyes, white dress, flowers in hair, gentle expression", "file": "portrait_A3.png"},
    "B": {"prompt": "masterpiece, best quality, 1girl, anime style, pink hair, green eyes, black leather jacket, confident smile, urban background", "file": "portrait_B3.png"},
    "C": {"prompt": char_c_prompt, "file": "portrait_C3.png"}
}

# Check if portraits exist
need_gen = False
for k, v in portraits.items():
    if not os.path.exists(os.path.join(COMFYUI_INPUT, v["file"])):
        need_gen = True
        break

if need_gen:
    for k, v in portraits.items():
        gen_workflow = {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": v["prompt"], "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": char_neg, "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
            "5": {"class_type": "KSampler", "inputs": {
                "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
                "seed": hash(k) % 100000, "steps": 25, "cfg": 7.0,
                "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "denoise": 1.0
            }},
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": "char_" + k}}
        }
        pid = queue_prompt(gen_workflow, "gen_" + k)
        print(f"Generating portrait {k}: {pid}")
        result = wait(pid, timeout=300)
        if result and result.get("status", {}).get("status_str") == "success":
            for nid, out in result["outputs"].items():
                if "images" in out:
                    img = out["images"][0]
                    src = os.path.join(COMFYUI_OUTPUT, img.get("subfolder", ""), img["filename"])
                    dst = os.path.join(COMFYUI_INPUT, v["file"])
                    shutil.copy2(src, dst)
                    shutil.copy2(src, os.path.join(OUTPUT_DIR, v["file"]))
                    print(f"  Portrait {k}: {img['filename']}")
        else:
            print(f"  FAILED for {k}!")
            exit(1)
else:
    print("All portraits exist, skipping generation.")

# ============================================================
# STEP 2: 3-Character IP-Adapter Regional
# ============================================================
print("\n=== STEP 2: 3角色 IP-Adapter Regional ===")

# 3 regions: left 30%, center 40%, right 30%
prompt_a = "masterpiece, best quality, 1girl, silver hair, blue eyes, white dress, gentle expression, standing pose"
prompt_b = "masterpiece, best quality, 1girl, pink hair, green eyes, black leather jacket, confident, urban style"
prompt_c = "masterpiece, best quality, 1girl, purple hair, golden eyes, red kimono, elegant, traditional Japanese"

ip_workflow = {
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
    "7": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "ipadapter_sd15_model.safetensors"}},
    "10": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}},
    "5A": {"class_type": "LoadImage", "inputs": {"image": "portrait_A3.png"}},
    "5B": {"class_type": "LoadImage", "inputs": {"image": "portrait_B3.png"}},
    "5C": {"class_type": "LoadImage", "inputs": {"image": "portrait_C3.png"}},
    "2A": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_a, "clip": ["1", 1]}},
    "2B": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_b, "clip": ["1", 1]}},
    "2C": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_c, "clip": ["1", 1]}},
    "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "lowres, bad anatomy, bad hands, text, error, cropped, worst quality, low quality, blurry, deformed, watermark", "clip": ["1", 1]}},
    # Combine 3 prompts
    "24AB": {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["2A", 0], "conditioning_2": ["2B", 0]}},
    "24": {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["24AB", 0], "conditioning_2": ["2C", 0]}},
    # 3 masks: left 30%, center 35%, right 30% (with 2.5% gaps)
    "40A": {"class_type": "MaskRectArea", "inputs": {"x": 0, "y": 0, "width": 30, "height": 100, "blur_radius": 5}},
    "40B": {"class_type": "MaskRectArea", "inputs": {"x": 32.5, "y": 0, "width": 35, "height": 100, "blur_radius": 5}},
    "40C": {"class_type": "MaskRectArea", "inputs": {"x": 67.5, "y": 0, "width": 32.5, "height": 100, "blur_radius": 5}},
    # 3 IPAdapter nodes chained
    "50A": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["1", 0], "ipadapter": ["10", 0], "image": ["5A", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["40A", 0], "clip_vision": ["7", 0]
    }},
    "50B": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["50A", 0], "ipadapter": ["10", 0], "image": ["5B", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["40B", 0], "clip_vision": ["7", 0]
    }},
    "50C": {"class_type": "IPAdapterAdvanced", "inputs": {
        "model": ["50B", 0], "ipadapter": ["10", 0], "image": ["5C", 0],
        "weight": 1.2, "weight_type": "ease out",
        "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "K+V w/ C penalty",
        "attn_mask": ["40C", 0], "clip_vision": ["7", 0]
    }},
    "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 1280, "height": 720, "batch_size": 1}},
    "30": {"class_type": "KSampler", "inputs": {
        "model": ["50C", 0], "positive": ["24", 0], "negative": ["3", 0],
        "latent_image": ["4", 0],
        "seed": 12345, "steps": 30, "cfg": 7.0,
        "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "denoise": 1.0
    }},
    "31": {"class_type": "VAEDecode", "inputs": {"samples": ["30", 0], "vae": ["1", 2]}},
    "32": {"class_type": "SaveImage", "inputs": {"images": ["31", 0], "filename_prefix": "triple_frame"}}
}

pid = queue_prompt(ip_workflow, "triple_ip")
print(f"3-Character IP-Adapter queued: {pid}")
result = wait(pid, timeout=600)
if not result or result.get("status", {}).get("status_str") != "success":
    print("FAILED!")
    if result:
        for m in result.get("status", {}).get("messages", []):
            print(json.dumps(m)[:300])
    exit(1)

frame_file = None
for nid, out in result["outputs"].items():
    if "images" in out:
        for img in out["images"]:
            frame_file = img["filename"]

src = os.path.join(COMFYUI_OUTPUT, frame_file)
shutil.copy2(src, os.path.join(COMFYUI_INPUT, "triple_frame.png"))
shutil.copy2(src, os.path.join(OUTPUT_DIR, "triple_frame.png"))
print(f"3-Character frame: {frame_file}")

# ============================================================
# STEP 3: Wan I2V Video
# ============================================================
print("\n=== STEP 3: Wan I2V 视频生成 ===")

vid_workflow = {
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
    }},
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "three anime girls in a beautiful scene, dynamic camera movement, cherry blossoms falling, soft warm lighting, cinematic anime, smooth gentle motion, depth of field, commercial quality",
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
    "67": {"class_type": "LoadImage", "inputs": {"image": "triple_frame.png"}},
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
        "steps": 20, "cfg": 5.0, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "start_step": 0, "end_step": 10
    }},
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 20, "cfg": 5.0, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "samples": ["27", 0], "start_step": 10, "end_step": -1
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "samples": ["90", 0], "vae": ["38", 0],
        "enable_vae_tiling": True,
        "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128
    }},
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": 8.0, "loop_count": 0,
        "filename_prefix": "triple_video",
        "format": "video/h264-mp4", "pingpong": False, "save_output": True
    }}
}

pid2 = queue_prompt(vid_workflow, "triple_vid")
print(f"Wan I2V queued: {pid2}")
result2 = wait(pid2, timeout=1800)
if not result2 or result2.get("status", {}).get("status_str") != "success":
    print("Video FAILED!")
    if result2:
        for m in result2.get("status", {}).get("messages", []):
            print(json.dumps(m)[:300])
    exit(1)

video_file = None
for nid, out in result2["outputs"].items():
    if "gifs" in out:
        for v in out["gifs"]:
            video_file = v["filename"]
            subfolder = v.get("subfolder", "")

src = os.path.join(COMFYUI_OUTPUT, subfolder, video_file) if subfolder else os.path.join(COMFYUI_OUTPUT, video_file)
dst = os.path.join(OUTPUT_DIR, "triple_video.mp4")
shutil.copy2(src, dst)
print(f"\n=== DONE! ===")
print(f"Video: {dst}")
print(f"Size: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
