import json, urllib.request

# Use CLIPVisionLoader instead of LoadWanVideoClipTextEncoder
wf = {
    "10": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "fp16",
        "quantization": "fp8_e4m3fn_fast",
        "load_device": "offload_device"
    }},
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "precision": "fp32"
    }},
    "12": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "smooth camera panning right, gentle waves moving, golden light",
        "negative_prompt": "blurry, ugly"
    }},
    "13": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan2.2_vae.safetensors",
        "precision": "bf16"
    }},
    "14": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
    "20": {"class_type": "CLIPVisionLoader", "inputs": {
        "clip_name": "CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors"
    }},
    "15": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["20", 0],
        "image_1": ["14", 0],
        "strength_1": 1.0,
        "strength_2": 1.0,
        "crop": "center",
        "combine_embeds": "concat",
        "force_offload": True
    }},
    "16": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": 832,
        "height": 480,
        "num_frames": 81,
        "noise_aug_strength": 0.0,
        "start_latent_strength": 1.0,
        "end_latent_strength": 1.0,
        "force_offload": True,
        "vae": ["13", 0],
        "clip_embeds": ["15", 0],
        "start_image": ["14", 0],
        "fun_or_fl2v_model": False
    }},
    "17": {"class_type": "WanVideoScheduler", "inputs": {
        "scheduler": "unipc",
        "steps": 30,
        "shift": 5.0,
        "start_step": 0,
        "end_step": 30
    }},
    "18": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["10", 0],
        "image_embeds": ["16", 0],
        "steps": 30,
        "cfg": 6.0,
        "shift": 5.0,
        "seed": 123,
        "force_offload": True,
        "scheduler": "unipc",
        "riflex_freq_index": 0
    }},
    "19": {"class_type": "WanVideoDecode", "inputs": {
        "vae": ["13", 0],
        "samples": ["18", 0],
        "enable_vae_tiling": True,
        "tile_x": 256,
        "tile_y": 256,
        "tile_stride_x": 128,
        "tile_stride_y": 128
    }},
    "21": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["19", 0],
        "filename_prefix": "pipeline_video",
        "fps": 16.0,
        "lossless": False,
        "quality": 90,
        "method": "default"
    }}
}

data = json.dumps({"prompt": wf}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f"OK: {result['prompt_id']}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
