import json
import urllib.request
import time

prompts = [
    {
        "name": "hidream_ice_queen",
        "text": "an ethereal ice queen sitting on a frozen throne, wearing a crown of crystalline icicles, translucent blue gown flowing like glaciers, aurora borealis swirling above, frozen palace interior with massive ice pillars, volumetric cold mist, blue and cyan color palette, ultra detailed, 8k cinematic",
        "neg": "blurry, low quality, warm colors, fire, ugly",
        "w": 832, "h": 1216, "seed": 1234, "steps": 40, "cfg": 5.0
    },
    {
        "name": "hidream_space_battle",
        "text": "an epic space battle between massive starships, laser beams and explosions in deep space, a giant mothership emerging from a wormhole, debris field with burning wreckage, nebula backdrop with purple and orange gas clouds, lens flare, volumetric lighting, cinematic wide shot, 8k sci-fi masterpiece",
        "neg": "blurry, low quality, cartoon, flat, daytime",
        "w": 1216, "h": 832, "seed": 5678, "steps": 40, "cfg": 5.5
    },
    {
        "name": "hidream_dragon_temple",
        "text": "a golden dragon coiled around an ancient mountain temple at sunset, scales reflecting warm orange light, cherry blossom petals floating in the wind, misty valleys below, intricate Chinese architecture with red pillars and curved roofs, god rays breaking through clouds, epic fantasy landscape, 8k masterpiece",
        "neg": "blurry, low quality, modern, ugly, distorted dragon",
        "w": 1216, "h": 832, "seed": 9999, "steps": 40, "cfg": 5.0
    },
    {
        "name": "hidream_neon_city",
        "text": "a lone figure walking through a rain-soaked neon alley in a futuristic megacity, towering holographic advertisements in Japanese and Chinese, steam rising from street vents, puddles reflecting pink and cyan neon signs, cinematic noir atmosphere, blade runner inspired, volumetric fog, 8k photorealistic",
        "neg": "blurry, low quality, bright daylight, cartoon, ugly",
        "w": 832, "h": 1216, "seed": 4321, "steps": 40, "cfg": 5.0
    }
]

base_workflow = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
    "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "PLACEHOLDER"}}
}

prompt_ids = []

for p in prompts:
    wf = json.loads(json.dumps(base_workflow))
    wf["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": p["text"], "clip": ["2", 0]}}
    wf["5"] = {"class_type": "CLIPTextEncode", "inputs": {"text": p["neg"], "clip": ["2", 0]}}
    wf["6"] = {"class_type": "EmptyLatentImage", "inputs": {"width": p["w"], "height": p["h"], "batch_size": 1}}
    wf["7"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "seed": p["seed"], "steps": p["steps"], "cfg": p["cfg"],
        "sampler_name": "dpmpp_2m_sde", "scheduler": "karras",
        "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0
    }}
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    wf["9"]["inputs"]["filename_prefix"] = p["name"]
    
    data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        prompt_ids.append({"name": p["name"], "id": result["prompt_id"]})
        print(f"SUBMITTED: {p['name']} -> {result['prompt_id']}", flush=True)
    except Exception as e:
        print(f"ERROR: {p['name']} -> {e}", flush=True)
    time.sleep(1)

print(f"\nTotal submitted: {len(prompt_ids)}", flush=True)
print(json.dumps(prompt_ids, indent=2), flush=True)
