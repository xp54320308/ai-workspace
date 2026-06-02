import json
import urllib.request

wf = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "an ethereal ice queen sitting on a frozen throne, 8k cinematic", "clip": ["2", 0]}},
    "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality", "clip": ["2", 0]}},
    "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
    "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 1234, "steps": 40, "cfg": 5.0, "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
    "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "hidream_test2"}}
}

data = json.dumps({"prompt": wf}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
