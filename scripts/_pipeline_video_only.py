"""单独跑视频生成（首帧已就位）"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"

def queue_prompt(w, cid="video"):
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

print("Generating video from pipeline_demo_frame...")

workflow = {
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
    }},
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": "cinematic anime scene, two characters on cherry blossom street, gentle breeze, hair flowing softly, petals drifting, slow camera pan right, warm golden hour lighting, peaceful atmosphere",
        "negative_prompt": "static, no motion, stiff, boring, low quality, blurry, artifacts",
        "t5": ["11", 0]
    }},
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16",
        "quantization": "disabled",
        "load_device": "offload_device"
    }},
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan_2.1_vae.safetensors", "precision": "bf16"
    }},
    "66": {"class_type": "CLIPVisionLoader", "inputs": {
        "clip_name": "clip_vision_h.safetensors"
    }},
    "67": {"class_type": "LoadImage", "inputs": {"image": "pipeline_demo_frame.png"}},
    "68": {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["66", 0], "image_1": ["67", 0],
        "strength_1": 1.0, "strength_2": 1.0, "crop": "center",
        "combine_embeds": "concat", "force_offload": True
    }},
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": 832, "height": 480, "num_frames": 81,
        "noise_aug_strength": 0.02, "start_latent_strength": 0.9,
        "end_latent_strength": 1.0, "force_offload": True,
        "vae": ["38", 0], "clip_embeds": ["68", 0],
        "start_image": ["67", 0], "fun_or_fl2v_model": False, "tiled_vae": False
    }},
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": 20, "cfg": 5.0, "shift": 8.0, "seed": 42,
        "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True
    }},
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "samples": ["27", 0], "vae": ["38", 0],
        "enable_vae_tiling": True, "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128
    }},
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": 8.0, "loop_count": 0,
        "filename_prefix": "pipeline_video",
        "format": "video/h264-mp4", "pingpong": False, "save_output": True
    }}
}

pid = queue_prompt(workflow, "pipeline_video")
print(f"Queued: {pid}")
result = wait(pid, timeout=1800)
if not result:
    print("FAILED!")
    exit(1)

video_file = None
for nid, out in result["outputs"].items():
    if "gifs" in out:
        for v in out["gifs"]:
            video_file = v["filename"]

src = os.path.join(COMFYUI_OUTPUT, video_file)
dst = os.path.join(OUTPUT_DIR, "pipeline_demo_video.mp4")
shutil.copy2(src, dst)
print(f"\nDONE! Video: {dst}")
print(f"Size: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
