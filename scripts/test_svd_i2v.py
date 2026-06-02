import json, urllib.request

# SVD XT - pass CLIP_VISION directly, not encoded output
wf = {
    "1": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {
        "ckpt_name": "svd_xt.safetensors"
    }},
    "2": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
    "4": {"class_type": "SVD_img2vid_Conditioning", "inputs": {
        "clip_vision": ["1", 1],
        "init_image": ["2", 0],
        "vae": ["1", 2],
        "width": 832,
        "height": 480,
        "video_frames": 25,
        "motion_bucket_id": 127,
        "fps": 8,
        "augmentation_level": 0.0
    }},
    "5": {"class_type": "KSampler", "inputs": {
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
    "6": {"class_type": "VAEDecode", "inputs": {
        "samples": ["5", 0],
        "vae": ["1", 2]
    }},
    "7": {"class_type": "SaveAnimatedWEBP", "inputs": {
        "images": ["6", 0],
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
