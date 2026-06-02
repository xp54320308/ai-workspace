import json, urllib.request, shutil, os

# First resize the keyframe to 704x704 (like the example)
# Then submit Wan 2.2 I2V 14B two-stage workflow

COMFYUI_INPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input'

# Copy and resize keyframe
src = r'C:\Users\qw\.openclaw\workspace\pipeline_test\pipeline_keyframe_00002_.png'
dst = os.path.join(COMFYUI_INPUT, 'pipeline_keyframe.png')
shutil.copy2(src, dst)

# Resize with PIL
from PIL import Image
img = Image.open(dst)
img = img.resize((704, 704), Image.LANCZOS)
img.save(dst)
print(f"Keyframe resized to 704x704", flush=True)

# Build workflow based on official example
# Two-stage: HIGH noise model (steps 0-3) → LOW noise model (steps 3-6)
wf = {
    # HIGH noise model loader
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "fp16_fast",
        "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device"
    }},
    # LOW noise model loader
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "fp16_fast",
        "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device"
    }},
    # Block swap for HIGH model
    "92": {"class_type": "WanVideoSetBlockSwap", "inputs": {
        "model": ["22", 0],
        "block_swap_args": ["39", 0]
    }},
    # Block swap for LOW model
    "93": {"class_type": "WanVideoSetBlockSwap", "inputs": {
        "model": ["71", 0],
        "block_swap_args": ["39", 0]
    }},
    # Block swap settings
    "39": {"class_type": "WanVideoBlockSwap", "inputs": {
        "blocks_to_swap": 20,
        "offload_img_emb": False,
        "offload_txt_emb": False,
        "offload_model": False,
        "extra_states": 1
    }},
    # T5 text encoder
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors",
        "precision": "bf16",
        "load_device": "offload_device",
        "quantization": "disabled"
    }},
    # Text encoding
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "t5": ["11", 0],
        "positive_prompt": "smooth camera slowly panning right, gentle ocean waves moving, golden sunset light reflecting on water, seagulls flying, cinematic peaceful atmosphere",
        "negative_prompt": "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的",
        "force_offload": True,
        "use_disk_cache": False,
        "device": "gpu"
    }},
    # VAE
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan2.2_vae.safetensors",
        "precision": "bf16"
    }},
    # Load keyframe
    "67": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
    # I2V encode (no clip vision needed for standard I2V!)
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "vae": ["38", 0],
        "start_image": ["67", 0],
        "width": 704,
        "height": 704,
        "num_frames": 81,
        "noise_aug_strength": 0.0,
        "start_latent_strength": 1.0,
        "end_latent_strength": 1.0,
        "force_offload": True,
        "fun_or_fl2v_model": False
    }},
    # Steps constant
    "94": {"class_type": "INTConstant", "inputs": {
        "value": 6
    }},
    # Split step
    "91": {"class_type": "INTConstant", "inputs": {
        "value": 3
    }},
    # CFG schedule
    "95": {"class_type": "CreateCFGScheduleFloatList", "inputs": {
        "steps": ["94", 0],
        "cfg_scale_start": 2,
        "cfg_scale_end": 2,
        "interpolation": "linear",
        "start_percent": 0,
        "end_percent": 1.0
    }},
    # Sampler 1: HIGH noise (steps 0-3)
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["92", 0],
        "image_embeds": ["89", 0],
        "text_embeds": ["16", 0],
        "steps": 6,
        "cfg": ["95", 0],
        "shift": 8,
        "seed": 42,
        "force_offload": True,
        "scheduler": "dpm++_sde",
        "riflex_freq_index": 0,
        "end_step": ["91", 0]
    }},
    # Sampler 2: LOW noise (steps 3-6)
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["93", 0],
        "image_embeds": ["89", 0],
        "text_embeds": ["16", 0],
        "samples": ["27", 0],
        "steps": 6,
        "cfg": ["95", 0],
        "shift": 8,
        "seed": 42,
        "force_offload": True,
        "scheduler": "dpm++_sde",
        "riflex_freq_index": 0,
        "start_step": ["91", 0]
    }},
    # Decode
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "vae": ["38", 0],
        "samples": ["90", 0],
        "enable_vae_tiling": True,
        "tile_x": 272,
        "tile_y": 272,
        "tile_stride_x": 144,
        "tile_stride_y": 128
    }},
    # Save as animated webp
    "60": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["28", 0],
        "filename_prefix": "wan_i2v_final",
        "fps": 16,
        "lossless": False,
        "quality": 85,
        "method": "default"
    }}
}

data = json.dumps({"prompt": wf}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f"Submitted: {result['prompt_id']}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
