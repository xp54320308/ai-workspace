"""
测试 2: 不同运动类型
用同一个首帧，测试 4 种不同运动 prompt
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
COMFYUI_INPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

def queue_prompt(w, cid="test2"):
    data = json.dumps({"prompt": w, "client_id": cid}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]

def wait(pid, timeout=1800):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = json.loads(urllib.request.urlopen(COMFYUI + "/history/" + pid).read())
            if pid in r:
                status = r[pid].get("status", {})
                if status.get("completed"):
                    return r[pid]
                if status.get("status_str") == "error":
                    for m in status.get("messages", []):
                        if m[0] == "execution_error":
                            print(f"  ERROR: {m[1].get('exception_message', '?')}")
                    return None
        except: pass
        time.sleep(10)
        print('.', end='', flush=True)
    return None

motions = [
    {
        "name": "pan_right",
        "prompt": "smooth camera pan right, characters walking forward, cherry blossom petals falling, gentle wind, cinematic tracking shot, anime style",
        "neg": "static, no motion, stiff, low quality",
        "shift": 8.0,
        "start_latent_strength": 0.9
    },
    {
        "name": "zoom_in",
        "prompt": "slow zoom in on characters, dramatic close up, eyes sparkling, hair details, emotional moment, soft focus background, anime cinematic",
        "neg": "static, no motion, blurry, low quality",
        "shift": 6.0,
        "start_latent_strength": 0.95
    },
    {
        "name": "dynamic_action",
        "prompt": "fast camera movement, characters running, speed lines, dramatic perspective, energetic motion, hair whipping in wind, action scene, anime style",
        "neg": "static, slow, stiff, boring, still frame, low quality",
        "shift": 12.0,
        "start_latent_strength": 0.8
    },
    {
        "name": "gentle_breeze",
        "prompt": "gentle breeze, hair flowing softly, cherry blossom petals drifting, subtle breathing motion, peaceful atmosphere, warm lighting, anime style",
        "neg": "static, stiff, no motion, low quality, blurry",
        "shift": 5.0,
        "start_latent_strength": 0.95
    }
]

for m in motions:
    print(f"\n=== Motion: {m['name']} (shift={m['shift']}) ===")

    workflow = {
        "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
            "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
        }},
        "16": {"class_type": "WanVideoTextEncode", "inputs": {
            "positive_prompt": m["prompt"],
            "negative_prompt": m["neg"],
            "t5": ["11", 0]
        }},
        "22": {"class_type": "WanVideoModelLoader", "inputs": {
            "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
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
            "width": 832, "height": 480, "num_frames": 81,
            "noise_aug_strength": 0.02, "start_latent_strength": m["start_latent_strength"],
            "end_latent_strength": 1.0, "force_offload": True,
            "vae": ["38", 0], "clip_embeds": ["68", 0], "start_image": ["67", 0],
            "fun_or_fl2v_model": False, "tiled_vae": False
        }},
        "27": {"class_type": "WanVideoSampler", "inputs": {
            "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
            "steps": 20, "cfg": 5.0, "shift": m["shift"], "seed": 42,
            "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
            "start_step": 0, "end_step": -1
        }},
        "28": {"class_type": "WanVideoDecode", "inputs": {
            "samples": ["27", 0], "vae": ["38", 0],
            "enable_vae_tiling": True,
            "tile_x": 272, "tile_y": 272,
            "tile_stride_x": 144, "tile_stride_y": 128
        }},
        "60": {"class_type": "VHS_VideoCombine", "inputs": {
            "images": ["28", 0], "frame_rate": 8.0, "loop_count": 0,
            "filename_prefix": f"test2_{m['name']}",
            "format": "video/h264-mp4", "pingpong": False, "save_output": True
        }}
    }

    pid = queue_prompt(workflow, f"test2_{m['name']}")
    print(f"Queued: {pid}")
    result = wait(pid, timeout=1800)
    if not result:
        print(f"FAILED: {m['name']}")
        continue

    video_file = None
    for nid, out in result["outputs"].items():
        if "gifs" in out:
            for v in out["gifs"]:
                video_file = v["filename"]
                if v.get("subfolder"):
                    video_file = os.path.join(v["subfolder"], video_file)

    src = os.path.join(COMFYUI_OUTPUT, video_file)
    dst = os.path.join(OUTPUT_DIR, f"test2_{m['name']}.mp4")
    shutil.copy2(src, dst)
    print(f"Done: {dst} ({os.path.getsize(dst)/1024/1024:.1f}MB)")

print("\n=== ALL MOTION TESTS DONE! ===")
