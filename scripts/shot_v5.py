"""Shot v5: Full WanVideoWrapper with T5 loader"""
import json, time, shutil, urllib.request
from pathlib import Path
import av

BASE = "http://127.0.0.1:8188"
COMFY_ROOT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI")
INPUT_DIR = COMFY_ROOT / "input"
OUTPUT_DIR = COMFY_ROOT / "output"
RUN_TAG = f"shot_v5_{time.strftime('%Y%m%d_%H%M%S')}"
RUN_DIR = OUTPUT_DIR / RUN_TAG
RUN_DIR.mkdir(parents=True, exist_ok=True)

REF = "aki_story_ref.png"
W, H = 832, 480
STYLE = "anime girl, long black hair, amber eyes, navy sailor uniform, wooden window, sunset, soft lighting, high quality"
NEG = "blurry, deformed, bad hands, extra fingers, different person, watermark, text, frozen, over-saturated, red skin, neon colors"

def api_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
def api_get(path):
    return json.loads(urllib.request.urlopen(f"{BASE}{path}", timeout=30).read())
def wait_for(pid, timeout=1800, poll=5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = api_get(f"/history/{pid}")
            if pid in h: return h[pid]
        except: pass
        time.sleep(poll)
    raise TimeoutError("Timeout")
def find_out(pattern, after):
    for p in sorted(OUTPUT_DIR.rglob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.stat().st_mtime > after: return p
    return None
def copy_in(src, name):
    shutil.copy2(src, INPUT_DIR / name)

def gen_keyframe(prompt_text, seed, ref_img=REF):
    p = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2509_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": ref_img}},
        "5": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Edit-2509-Multiple-angles.safetensors", "strength_model": 0.8}},
        "6": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["5", 0], "lora_name": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["4", 0], "prompt": f"Keep the same girl, same face, same clothes. {prompt_text}"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["9", 0], "seed": seed, "steps": 4, "cfg": 5.5, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": f"{RUN_TAG}/kf"}}
    }
    t = time.time()
    wait_for(api_post("/prompt", {"prompt": p})["prompt_id"])
    return find_out("kf_*.png", t - 5)


# ── Generate keyframes ──
print(f"[{RUN_TAG}] Generating keyframes...")
kf_start = gen_keyframe("She is sitting quietly by the wooden window, looking outside. Hands on lap. Curtain still. Calm.", seed=20260507701)
print(f"  Start: {kf_start.name}")
kf_end = gen_keyframe("Same girl. She raised her right hand to cup her cheek. Hair flutters. Curtain billows. Thoughtful.", seed=20260507702)
print(f"  End: {kf_end.name}")

# ── I2V with WanVideoWrapper + T5 ──
print(f"\n[{RUN_TAG}] I2V (WanVideoWrapper + T5)...")
copy_in(kf_start, "i2v_start.png")
copy_in(kf_end, "i2v_end.png")

positive = f"{STYLE}, smooth animation, sitting to raising hand to cheek, curtain billows, hair flutters, camera push-in, 5 second shot"

prompt = {
    # T5 text encoder loader
    "T5": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors",
        "precision": "bf16",
        "load_device": "offload_device",
        "quantization": "disabled"
    }},
    # Model loaders
    "M1": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "fp16_fast", "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device", "attention_mode": "comfy", "rms_norm_function": "default"
    }},
    "M2": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "fp16_fast", "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device", "attention_mode": "comfy", "rms_norm_function": "default"
    }},
    # VAE
    "V": {"class_type": "WanVideoVAELoader", "inputs": {"model_name": "wan2.2_vae.safetensors", "precision": "bf16"}},
    # CLIP text encode
    "T": {"class_type": "WanVideoTextEncode", "inputs": {
        "t5": ["T5", 0], "positive_prompt": positive, "negative_prompt": NEG,
        "force_offload": True, "use_disk_cache": False, "device": "gpu"
    }},
    # CLIP Vision
    "CV": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "CVE": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["CV", 0], "image_1": ["LS", 0], "image_2": ["LE", 0],
        "strength_1": 1.0, "strength_2": 1.0, "crop": "center",
        "combine_embeds": "average", "force_offload": True
    }},
    # Load images
    "LS": {"class_type": "LoadImage", "inputs": {"image": "i2v_start.png"}},
    "LE": {"class_type": "LoadImage", "inputs": {"image": "i2v_end.png"}},
    # Image to video encode with noise_aug and reduced latent_strength
    "IE": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": W, "height": H, "num_frames": 81,
        "noise_aug_strength": 0.02, "start_latent_strength": 0.85, "end_latent_strength": 0.85,
        "force_offload": True, "vae": ["V", 0],
        "clip_embeds": ["CVE", 0], "start_image": ["LS", 0], "end_image": ["LE", 0],
        "fun_or_fl2v_model": True, "tiled_vae": False, "augment_empty_frames": 0.0
    }},
    # Sampler stage 1 (high noise)
    "S1": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["M1", 0], "image_embeds": ["IE", 0], "text_embeds": ["T", 0],
        "steps": 22, "cfg": 4.0, "shift": 8.0, "seed": 20260507711,
        "scheduler": "unipc", "riflex_freq_index": 0, "rope_function": "comfy",
        "force_offload": True, "start_step": 0, "end_step": 11,
        "add_noise_to_samples": True
    }},
    # Sampler stage 2 (low noise)
    "S2": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["M2", 0], "image_embeds": ["IE", 0], "text_embeds": ["T", 0],
        "samples": ["S1", 0], "steps": 22, "cfg": 4.0, "shift": 8.0, "seed": 20260507711,
        "scheduler": "unipc", "riflex_freq_index": 0, "rope_function": "comfy",
        "force_offload": True, "start_step": 11, "end_step": 22,
        "add_noise_to_samples": False
    }},
    # Decode
    "D": {"class_type": "WanVideoDecode", "inputs": {
        "vae": ["V", 0], "samples": ["S2", 0], "enable_vae_tiling": False,
        "tile_x": 272, "tile_y": 272, "tile_stride_x": 144, "tile_stride_y": 128, "normalization": "default"
    }},
    # Save
    "O": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["D", 0], "frame_rate": 16, "loop_count": 0,
        "filename_prefix": f"{RUN_TAG}/raw", "format": "video/h264-mp4",
        "pingpong": False, "save_output": True, "pix_fmt": "yuv420p",
        "crf": 19, "save_metadata": True, "trim_to_audio": False
    }}
}

t = time.time()
try:
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=1800)
    raw = find_out("raw_*.mp4", t - 5)
    if raw:
        print(f"  Raw: {raw.name} ({raw.stat().st_size//1024}KB)")
    else:
        # Check for any new mp4 files
        for p in sorted(OUTPUT_DIR.rglob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.stat().st_mtime > t - 10:
                raw = p
                print(f"  Raw: {raw.name} ({raw.stat().st_size//1024}KB)")
                break
        if not raw:
            print("  ERROR: No video output found")
            raise SystemExit(1)
except urllib.error.HTTPError as e:
    err = e.read().decode()[:800]
    print(f"  ERROR: {err}")
    raise

# ── RIFE ──
print(f"\n[{RUN_TAG}] RIFE...")
copy_in(raw, "rife_in.mp4")
rife_p = {
    "1": {"class_type": "LoadVideo", "inputs": {"file": "rife_in.mp4"}},
    "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
    "3": {"class_type": "RIFE VFI", "inputs": {"frames": ["2", 0], "ckpt_name": "rife49.pth", "clear_cache_after_n_frames": 8, "multiplier": 2, "fast_mode": True, "ensemble": True, "scale_factor": 1.0, "dtype": "float16", "torch_compile": False, "batch_size": 1}},
    "4": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["3", 0], "frame_rate": 32, "loop_count": 0, "filename_prefix": f"{RUN_TAG}/final", "format": "video/h264-mp4", "pingpong": False, "save_output": True, "pix_fmt": "yuv420p", "crf": 18, "save_metadata": True, "trim_to_audio": False}}
}
t = time.time()
result = wait_for(api_post("/prompt", {"prompt": rife_p})["prompt_id"], timeout=600)
final = find_out("final_*.mp4", t - 5)
if not final:
    for p in sorted(OUTPUT_DIR.rglob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.stat().st_mtime > t - 10 and "final" in p.name:
            final = p
            break
print(f"  Final: {final.name} ({final.stat().st_size//1024}KB)")

# ── Review ──
rd = RUN_DIR / "review"
rd.mkdir(exist_ok=True)
with av.open(str(final)) as c:
    for i, f in enumerate(c.decode(video=0)):
        if i % 32 == 0:
            f.to_image().save(str(rd / f"f_{i:04d}.png"))
print(f"\nDone! {RUN_DIR}")
