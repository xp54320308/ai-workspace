import json
import urllib.request
import time

prompts = [
    {
        "name": "hd_landscape",
        "text": "a breathtaking mountain landscape at golden hour, dramatic clouds lit by setting sun, crystal clear lake reflecting snow-capped peaks, wildflower meadow in foreground, god rays through cloud gaps, ultra sharp, National Geographic photography, 8k masterpiece",
        "neg": "blurry, low quality, oversaturated, cartoon, ugly",
        "w": 1216, "h": 832, "seed": 1111, "cfg": 4.5
    },
    {
        "name": "hd_mecha",
        "text": "a giant red mecha robot standing in a destroyed city, glowing blue eyes, smoke and debris, dramatic low angle shot, cinematic lighting, intricate mechanical details, hydraulics and armor plates visible, 8k photorealistic",
        "neg": "blurry, low quality, cartoon, flat lighting, ugly",
        "w": 832, "h": 1216, "seed": 2222, "cfg": 5.0
    },
    {
        "name": "hd_ocean",
        "text": "a massive kraken emerging from a stormy ocean, tentacles wrapping around a wooden sailing ship, huge waves crashing, lightning illuminating the scene, dark dramatic atmosphere, epic scale, cinematic masterpiece, 8k ultra detailed",
        "neg": "blurry, low quality, calm, cartoon, bright daylight",
        "w": 1216, "h": 832, "seed": 3333, "cfg": 5.0
    },
    {
        "name": "hd_food",
        "text": "a gourmet sushi platter on a black slate board, fresh salmon and tuna nigiri with glistening wasabi, pickled ginger, soy sauce in ceramic dish, bokeh background of a high-end Japanese restaurant, food photography, macro lens, 8k appetizing",
        "neg": "blurry, low quality, unappetizing, plastic looking, ugly",
        "w": 1024, "h": 1024, "seed": 4444, "cfg": 4.5
    },
    {
        "name": "hd_abstract",
        "text": "abstract fluid art, swirling iridescent liquid metal in gold silver and deep purple, metallic reflections, smooth gradients, organic flowing shapes, dark background, luxury aesthetic, 8k wallpaper quality",
        "neg": "blurry, low quality, flat, dull, noisy",
        "w": 1216, "h": 832, "seed": 5555, "cfg": 4.0
    }
]

prompt_ids = []
for p in prompts:
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": p["text"], "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": p["neg"], "clip": ["2", 0]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": p["w"], "height": p["h"], "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "seed": p["seed"], "steps": 50, "cfg": p["cfg"],
            "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": p["name"]}}
    }
    data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        prompt_ids.append({"name": p["name"], "id": result["prompt_id"]})
        print(f"SUBMITTED: {p['name']}", flush=True)
    except urllib.error.HTTPError as e:
        print(f"ERROR: {p['name']} -> {e.code}: {e.read().decode()}", flush=True)
    time.sleep(2)

print(f"\nTotal: {len(prompt_ids)}", flush=True)

# Wait for all
done_set = set()
for i in range(120):
    time.sleep(10)
    try:
        req = urllib.request.Request("http://127.0.0.1:8188/history")
        resp = urllib.request.urlopen(req, timeout=10)
        history = json.loads(resp.read())
        for p in prompt_ids:
            if p["id"] in history and p["id"] not in done_set:
                done_set.add(p["id"])
                imgs = history[p["id"]].get("outputs", {}).get("9", {}).get("images", [])
                print(f"DONE [{len(done_set)}/{len(prompt_ids)}]: {p['name']} -> {imgs[0]['filename'] if imgs else '?'}", flush=True)
        if len(done_set) >= len(prompt_ids):
            print("\nALL DONE!", flush=True)
            break
        req2 = urllib.request.Request("http://127.0.0.1:8188/queue")
        resp2 = urllib.request.urlopen(req2, timeout=10)
        q = json.loads(resp2.read())
        print(f"[{(i+1)*10}s] Done: {len(done_set)}/{len(prompt_ids)}, Queue: {len(q.get('queue_running',[]))}R/{len(q.get('queue_pending',[]))}P", flush=True)
    except Exception as e:
        print(f"[{(i+1)*10}s] {e}", flush=True)
