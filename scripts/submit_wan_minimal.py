import json, urllib.request, shutil, os
from PIL import Image

COMFYUI_INPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input'
src = r'C:\Users\qw\.openclaw\workspace\pipeline_test\pipeline_keyframe_00002_.png'
dst = os.path.join(COMFYUI_INPUT, 'pipeline_keyframe.png')
img = Image.open(src)
img = img.resize((832, 480), Image.LANCZOS)
img.save(dst)

# Minimal test: 5B model, no text, no extras, just see if sampling works
wf = {
    "10": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_ti2v_5B_fp16.safetensors",
        "base_precision": "fp16",
        "quantization": "disabled",
        "load_device": "offload_device"
    }},
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan2.2_vae.safetensors",
        "precision": "bf16"
    }},
    "67": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
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
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["10", 0],
        "image_embeds": ["89", 0],
        "steps": 30,
        "cfg": 6.0,
        "shift": 5.0,
        "seed": 42,
        "force_offload": True,
        "scheduler": "unipc",
        "riflex_freq_index": 0
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "vae": ["38", 0],
        "samples": ["27", 0],
        "enable_vae_tiling": True,
        "tile_x": 256,
        "tile_y": 256,
        "tile_stride_x": 128,
        "tile_stride_y": 128
    }},
    "60": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["28", 0],
        "filename_prefix": "wan_i2v_test",
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
