import json
import urllib.request

prompt = "a beautiful woman warrior in ornate silver armor, standing in a grand cathedral with stained glass windows, sunlight streaming through colored glass casting rainbow light on her armor, intricate engravings on the armor plates, flowing red cape, holding a glowing sword, photorealistic, ultra detailed, 8k masterpiece"

neg = "blurry, low quality, distorted, ugly, cartoon, anime, soft focus"

# Test 1: t5xxl_fp16 + 50 steps + dpmpp_2m + karras
wf = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
    "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "seed": 2026, "steps": 50, "cfg": 4.5,
        "sampler_name": "dpmpp_2m", "scheduler": "karras",
        "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0
    }},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "hidream_sharp"}}
}

data = json.dumps({"prompt": wf}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f"SUBMITTED: {result['prompt_id']}", flush=True)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"ERROR {e.code}: {body}", flush=True)
