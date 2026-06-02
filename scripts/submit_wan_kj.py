import json, urllib.request, shutil, os
from PIL import Image

# Prepare keyframe
COMFYUI_INPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input'
src = r'C:\Users\qw\.openclaw\workspace\pipeline_test\pipeline_keyframe_00002_.png'
dst = os.path.join(COMFYUI_INPUT, 'pipeline_keyframe.png')
img = Image.open(src)
img = img.resize((832, 480), Image.LANCZOS)
img.save(dst)
print("Keyframe ready: 832x480", flush=True)

# Two-stage I2V: HIGH (0-3) + LOW (3-6)
wf = {
    # HIGH noise model
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "WanVideo\\2_2\\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors",
        "base_precision": "fp16_fast",
        "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device"
    }},
    # LOW noise model
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "WanVideo\\2_2\\Wan2_2-I2V-A14B-LOW_fp8_e4m3fn_scaled_KJ.safetensors",
        "base_precision": "fp16_fast",
        "quantization": "fp8_e4m3fn_scaled",
        "load_device": "offload_device"
    }},
    # Block swap settings
    "39": {"class_type": "WanVideoBlockSwap", "inputs": {
        "blocks_to_swap": 20,
        "offload_img_emb": False,
        "offload_txt_emb": False,
        "offload_model": False,
        "extra_states": 1
    }},
    # Block swap for HIGH
    "92": {"class_type": "WanVideoSetBlockSwap", "inputs": {
        "model": ["22", 0],
        "block_swap_args": ["39", 0]
    }},
    # Block swap for LOW
    "93": {"class_type": "WanVideoSetBlockSwap", "inputs": {
        "model": ["71", 0],
        "block_swap_args": ["39", 0]
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
        "positive_prompt": "smooth camera slowly panning right, gentle ocean waves moving, golden sunset light reflecting on water, seagulls flying across the sky, cinematic peaceful atmosphere, warm orange and purple sky",
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
    # I2V encode
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "vae": ["38", 0],
        "start_image": ["67", 0],
        "width": 832,
        "height": 480,
        "num_frames": 81,
        "noise_aug_strength": 0.0,
        "start_latent_strength": 1.0,
        "end_latent_strength": 1.0,
        "force_offload": True,
        "fun_or_fl2v_model": False
    }},
    # Steps
    "94": {"class_type": "INTConstant", "inputs": {"value": 6}},
    # Split step
    "91": {"class_type": "INTConstant", "inputs": {"value": 3}},
    # CFG schedule
    "95": {"class_type": "CreateCFGScheduleFloatList", "inputs": {
        "steps": ["94", 0],
        "cfg_scale_start": 2.0,
        "cfg_scale_end": 2.0,
        "interpolation": "linear",
        "start_percent": 0.0,
        "end_percent": 1.0
    }},
    # Sampler 1: HIGH noise
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
    # Sampler 2: LOW noise
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
    # Save
    "60": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["28", 0],
        "filename_prefix": "wan22_i2v_final",
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
