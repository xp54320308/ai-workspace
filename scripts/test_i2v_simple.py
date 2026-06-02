import json, urllib.request

# Use SVD XT as a simpler I2V test first
wf = {
    "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {
        "ckpt_name": "svd_xt.safetensors"
    }},
    "2": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
    "3": {"class_type": "CLIPVisionEncode", "inputs": {
        "clip_vision": ["1", 1],
        "image": ["2", 0]
    }},
    "4": {"class_type": "WanImageToVideo", "inputs": {
        "positive": ["5", 0],
        "negative": ["6", 0],
        "vae": ["1", 2],
        "width": 832,
        "height": 480,
        "length": 25,
        "batch_size": 1,
        "clip_vision_output": ["3", 0],
        "start_image": ["2", 0]
    }},
    "5": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "smooth camera panning, gentle waves, golden light",
        "clip": ["1", 1]
    }},
    "6": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "blurry, ugly",
        "clip": ["1", 1]
    }},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0],
        "seed": 42,
        "steps": 25,
        "cfg": 3.0,
        "sampler_name": "euler",
        "scheduler": "normal",
        "positive": ["4", 0],
        "negative": ["4", 1],
        "latent_image": ["4", 2],
        "denoise": 1.0
    }},
    "8": {"class_type": "VAEDecode", "inputs": {
        "samples": ["7", 0],
        "vae": ["1", 2]
    }},
    "9": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["8", 0],
        "filename_prefix": "pipeline_video",
        "fps": 8.0,
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
    print(f"OK: {result['prompt_id']}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
