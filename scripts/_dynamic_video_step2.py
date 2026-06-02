"""
Step 2: 动感视频生成
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"

def queue_prompt(w):
    data = json.dumps({"prompt": w, "client_id": "dyn2"}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]

w = {
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
    }},
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "dynamic action scene, two anime girls running through cherry blossom street, hair flowing wildly in wind, petals swirling around them, fast camera movement following characters, dramatic perspective shifts, energetic motion, speed lines, cinematic anime, vibrant colors, intense action",
        "negative_prompt": "static, no motion, slow, stiff, boring, still frame, low quality, blurry, artifacts",
        "t5": ["11", 0]
    }},
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
    }},
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
    }},
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan_2.1_vae.safetensors", "precision": "bf16"
    }},
    "66": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
    "67": {"class_type": "LoadImage", "inputs": {"image": "dynamic_frame.png"}},
    "68": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["66", 0], "image_1": ["67", 0],
        "strength_1": 1.0, "strength_2": 1.0,
        "crop": "center", "combine_embeds": "concat", "force_offload": True
    }},
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": 832, "height": 480, "num_frames": 121,
        "noise_aug_strength": 0.02, "start_latent_strength": 0.85,
        "end_latent_strength": 1.0, "force_offload": True,
        "vae": ["38", 0], "clip_embeds": ["68", 0], "start_image": ["67", 0],
        "fun_or_fl2v_model": False, "tiled_vae": False
    }},
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 25, "cfg": 5.5, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "start_step": 0, "end_step": 12
    }},
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 25, "cfg": 5.5, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
        "samples": ["27", 0], "start_step": 12, "end_step": -1
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "samples": ["90", 0], "vae": ["38", 0],
        "enable_vae_tiling": True,
        "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128
    }},
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": 8.0, "loop_count": 0,
        "filename_prefix": "dynamic_video",
        "format": "video/h264-mp4", "pingpong": False, "save_output": True
    }}
}

pid = queue_prompt(w)
print("Queued:", pid)

# Poll
import urllib.error
start = time.time()
while time.time() - start < 1200:
    try:
        r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
        if pid in r and r[pid].get("status", {}).get("completed"):
            print("DONE!")
            outputs = r[pid]["outputs"]
            for nid, out in outputs.items():
                if "gifs" in out:
                    for v in out["gifs"]:
                        video_file = v["filename"]
                        subfolder = v.get("subfolder", "")
                        src = os.path.join(COMFYUI_OUTPUT, subfolder, video_file) if subfolder else os.path.join(COMFYUI_OUTPUT, video_file)
                        dst = os.path.join(OUTPUT_DIR, "dynamic_video.mp4")
                        shutil.copy2(src, dst)
                        print(f"Video: {dst}")
                        print(f"Size: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
            break
    except: pass
    elapsed = int(time.time() - start)
    q = json.loads(urllib.request.urlopen(COMFYUI + "/queue").read())
    print(f"[{elapsed}s] Running: {len(q.get('queue_running', []))}")
    time.sleep(30)
else:
    print("TIMEOUT!")
