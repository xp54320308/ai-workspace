"""
测试 3: LTX-Video 2.3-22b-distilled I2V
使用正确的节点参数
"""
import urllib.request, json, time, os, shutil

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"

def queue_prompt(w, cid="test3"):
    data = json.dumps({"prompt": w, "client_id": cid}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]

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

print("=== TEST 3: LTX-Video 2.3-22b-distilled I2V ===")
print("Steps: 8, Resolution: 768x512, Frames: 97")

workflow = {
    # Load LTX diffusion model
    "1": {"class_type": "CheckpointLoaderSimple", "inputs": {
        "ckpt_name": "ltx-2.3-22b-distilled-fp8.safetensors"
    }},
    # Load LTX CLIP text encoder (Gemma/T5)
    "2": {"class_type": "LTXVGemmaCLIPModelLoader", "inputs": {
        "gemma_path": "umt5_xxl_fp16.safetensors",
        "ltxv_path": "ltx-2.3-22b-distilled-fp8.safetensors",
        "max_length": 1024
    }},
    # Encode positive prompt
    "3": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "cinematic anime scene, two characters on cherry blossom street, gentle breeze, hair flowing, camera pan right, warm golden hour lighting, high quality anime",
        "clip": ["2", 0]
    }},
    # Encode negative prompt
    "4": {"class_type": "CLIPTextEncode", "inputs": {
        "text": "static, no motion, low quality, blurry, artifacts, distorted",
        "clip": ["2", 0]
    }},
    # Load first frame
    "5": {"class_type": "LoadImage", "inputs": {"image": "dynamic_frame.png"}},
    # LTX Image to Video conditioning
    "6": {"class_type": "LTXVImgToVideo", "inputs": {
        "positive": ["3", 0],
        "negative": ["4", 0],
        "vae": ["1", 2],
        "image": ["5", 0],
        "width": 768,
        "height": 512,
        "length": 97,
        "batch_size": 1,
        "strength": 0.9
    }},
    # Set frame rate conditioning
    "7": {"class_type": "LTXVConditioning", "inputs": {
        "positive": ["6", 0],
        "negative": ["6", 1],
        "frame_rate": 25.0
    }},
    # Scheduler for sigmas
    "8": {"class_type": "LTXVScheduler", "inputs": {
        "steps": 8,
        "max_shift": 2.05,
        "base_shift": 0.95,
        "stretch": True,
        "terminal": 0.1
    }},
    # Apply STG to model
    "9": {"class_type": "LTXVApplySTG", "inputs": {
        "model": ["1", 0],
        "block_indices": "14, 19"
    }},
    # CFG Guider
    "10": {"class_type": "CFGGuider", "inputs": {
        "model": ["9", 0],
        "positive": ["7", 0],
        "negative": ["7", 1],
        "cfg": 3.0
    }},
    # Sampler
    "11": {"class_type": "KSamplerSelect", "inputs": {
        "sampler_name": "euler"
    }},
    # Random noise
    "12": {"class_type": "RandomNoise", "inputs": {
        "noise_seed": 42
    }},
    # Sample
    "13": {"class_type": "SamplerCustomAdvanced", "inputs": {
        "noise": ["12", 0],
        "guider": ["10", 0],
        "sampler": ["11", 0],
        "sigmas": ["8", 0],
        "latent_image": ["6", 2]
    }},
    # Decode
    "14": {"class_type": "VAEDecode", "inputs": {
        "samples": ["13", 0],
        "vae": ["1", 2]
    }},
    # Save video
    "15": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["14", 0],
        "frame_rate": 25.0,
        "loop_count": 0,
        "filename_prefix": "test3_ltx",
        "format": "video/h264-mp4",
        "pingpong": False,
        "save_output": True
    }}
}

pid = queue_prompt(workflow, "test3_ltx")
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
            if v.get("subfolder"):
                video_file = os.path.join(v["subfolder"], video_file)

src = os.path.join(COMFYUI_OUTPUT, video_file)
dst = os.path.join(OUTPUT_DIR, "test3_ltx.mp4")
shutil.copy2(src, dst)
print(f"\n=== DONE! ===")
print(f"Video: {dst}")
print(f"Size: {os.path.getsize(dst) / 1024 / 1024:.1f} MB")
