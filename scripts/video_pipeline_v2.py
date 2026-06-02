"""
端到端视频制作流水线 v2
流程: 关键帧(HiDream) → 视频(Wan 2.2 I2V 5B) → 语音(EdgeTTS) → 合成(FFmpeg)
"""
import json
import urllib.request
import time
import subprocess
import os
import shutil
import sys

WORKSPACE = r'C:\Users\qw\.openclaw\workspace'
OUTPUT_DIR = os.path.join(WORKSPACE, 'pipeline_test')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMFYUI_URL = 'http://127.0.0.1:8188'
COMFYUI_OUTPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output'
COMFYUI_INPUT = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input'

def submit_workflow(wf, label=""):
    data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    pid = result["prompt_id"]
    print(f"  [{label}] Submitted: {pid}", flush=True)
    return pid

def wait_for_prompt(pid, label="", timeout_min=10):
    for i in range(timeout_min * 6):
        try:
            req = urllib.request.Request(f"{COMFYUI_URL}/history")
            resp = urllib.request.urlopen(req, timeout=10)
            history = json.loads(resp.read())
            if pid in history:
                outputs = history[pid].get("outputs", {})
                status = history[pid].get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    print(f"  [{label}] ERROR: {messages[:3]}", flush=True)
                    return None
                print(f"  [{label}] DONE in ~{i*10}s", flush=True)
                return outputs
            if i % 6 == 0:
                req2 = urllib.request.Request(f"{COMFYUI_URL}/queue")
                resp2 = urllib.request.urlopen(req2, timeout=10)
                q = json.loads(resp2.read())
                r = len(q.get("queue_running", []))
                p = len(q.get("queue_pending", []))
                print(f"  [{label}] [{i*10}s] Queue: {r}R/{p}P", flush=True)
        except Exception as e:
            print(f"  [{label}] [{i*10}s] {e}", flush=True)
        time.sleep(10)
    print(f"  [{label}] TIMEOUT!", flush=True)
    return None

def copy_output(outputs, node_id, prefix="pipeline"):
    files = []
    if node_id in outputs:
        for img in outputs[node_id].get("images", []):
            src = os.path.join(COMFYUI_OUTPUT, img["filename"])
            dst = os.path.join(OUTPUT_DIR, img["filename"])
            if os.path.exists(src):
                shutil.copy2(src, dst)
                files.append(dst)
    if node_id in outputs:
        for vid in outputs[node_id].get("gifs", []):
            src = os.path.join(COMFYUI_OUTPUT, vid["filename"])
            dst = os.path.join(OUTPUT_DIR, vid["filename"])
            if os.path.exists(src):
                shutil.copy2(src, dst)
                files.append(dst)
    return files

def copy_to_input(src_path, filename):
    dst = os.path.join(COMFYUI_INPUT, filename)
    shutil.copy2(src_path, dst)
    return filename

# ============================================================
# STEP 1: Keyframe (HiDream) — already done, skip if exists
# ============================================================
def step1_keyframe():
    print("\n=== STEP 1: Keyframe ===", flush=True)
    existing = os.path.join(OUTPUT_DIR, 'pipeline_keyframe_00001_.png')
    if os.path.exists(existing):
        print(f"  Already exists: {existing}", flush=True)
        return existing
    
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "a beautiful sunset over a calm ocean, golden light reflecting on gentle waves, silhouette of a sailing boat in the distance, cinematic wide shot, warm orange and purple sky, photorealistic, 8k", "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, ugly", "clip": ["2", 0]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 480, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 42, "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "pipeline_keyframe"}}
    }
    pid = submit_workflow(wf, "keyframe")
    outputs = wait_for_prompt(pid, "keyframe", timeout_min=8)
    if not outputs:
        return None
    files = copy_output(outputs, "9")
    return files[0] if files else None

# ============================================================
# STEP 2: I2V (Wan 2.2 I2V 5B via WanVideoWrapper)
# ============================================================
def step2_i2v(keyframe_path):
    print("\n=== STEP 2: Image to Video (Wan 2.2 5B) ===", flush=True)
    input_filename = copy_to_input(keyframe_path, 'pipeline_keyframe.png')
    
    wf = {
        # Load model
        "10": {"class_type": "WanVideoModelLoader", "inputs": {
            "model": "wan2.2_ti2v_5B_fp16.safetensors",
            "base_precision": "fp16",
            "quantization": "disabled",
            "load_device": "offload_device"
        }},
        # Load text encoder
        "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
            "model_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "precision": "fp32"
        }},
        # Encode text
        "12": {"class_type": "WanVideoTextEncode", "inputs": {
            "positive_prompt": "smooth camera slowly panning right, gentle waves moving, seagulls flying across the sky, warm golden cinematic light, peaceful atmosphere",
            "negative_prompt": "blurry, distorted, ugly, static, no motion"
        }},
        # Load VAE
        "13": {"class_type": "WanVideoVAELoader", "inputs": {
            "model_name": "wan2.2_vae.safetensors"
        }},
        # Load keyframe
        "14": {"class_type": "LoadImage", "inputs": {
            "image": input_filename
        }},
        # Clip Vision encode
        "15": {"class_type": "WanVideoClipVisionEncode", "inputs": {
            "clip_vision": ["20", 0],
            "image_1": ["14", 0],
            "strength_1": 1.0,
            "strength_2": 1.0,
            "crop": "center",
            "combine_embeds": "concat",
            "force_offload": True
        }},
        # Load Clip Vision
        "20": {"class_type": "LoadWanVideoClipTextEncoder", "inputs": {
            "model_name": "clip_vision_h.safetensors"
        }},
        # Image to Video encode
        "16": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
            "width": 832,
            "height": 480,
            "num_frames": 81,
            "noise_aug_strength": 0.0,
            "start_latent_strength": 1.0,
            "end_latent_strength": 1.0,
            "force_offload": True,
            "vae": ["13", 0],
            "clip_embeds": ["15", 0],
            "start_image": ["14", 0],
            "fun_or_fl2v_model": True
        }},
        # Scheduler
        "17": {"class_type": "WanVideoScheduler", "inputs": {
            "scheduler": "unipc",
            "steps": 30,
            "shift": 5.0,
            "start_step": 0,
            "end_step": 30
        }},
        # Sampler
        "18": {"class_type": "WanVideoSampler", "inputs": {
            "model": ["10", 0],
            "image_embeds": ["16", 0],
            "steps": 30,
            "cfg": 6.0,
            "shift": 5.0,
            "seed": 123,
            "force_offload": True,
            "scheduler": "unipc",
            "riflex_freq_index": 0
        }},
        # Decode
        "19": {"class_type": "WanVideoDecode", "inputs": {
            "vae": ["13", 0],
            "samples": ["18", 0],
            "enable_vae_tiling": True,
            "tile_x": 256,
            "tile_y": 256,
            "tile_stride_x": 128,
            "tile_stride_y": 128
        }},
        # Save
        "21": {"class_type": "SaveAnimatedWEBP", "inputs": {
            "images": ["19", 0],
            "filename_prefix": "pipeline_video",
            "fps": 16.0,
            "lossless": False,
            "quality": 90,
            "method": "default"
        }}
    }
    pid = submit_workflow(wf, "i2v")
    outputs = wait_for_prompt(pid, "i2v", timeout_min=15)
    if not outputs:
        return None
    files = copy_output(outputs, "21")
    return files

# ============================================================
# STEP 3: TTS
# ============================================================
def step3_tts():
    print("\n=== STEP 3: TTS Audio ===", flush=True)
    text = "A beautiful sunset over the ocean. Golden light reflects on gentle waves as a sailing boat glides across the horizon."
    output_path = os.path.join(OUTPUT_DIR, 'narration.mp3')
    
    try:
        import edge_tts
        import asyncio
        async def gen():
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(output_path)
        asyncio.run(gen())
        if os.path.exists(output_path):
            print(f"  TTS: {output_path} ({os.path.getsize(output_path)/1024:.0f}KB)", flush=True)
            return output_path
    except Exception as e:
        print(f"  TTS error: {e}", flush=True)
    
    # Fallback: install and try
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'edge-tts', '-q'], capture_output=True, timeout=30)
        import edge_tts
        import asyncio
        async def gen():
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(output_path)
        asyncio.run(gen())
        if os.path.exists(output_path):
            print(f"  TTS (installed): {output_path}", flush=True)
            return output_path
    except Exception as e:
        print(f"  TTS fallback error: {e}", flush=True)
    
    return None

# ============================================================
# STEP 4: Assemble
# ============================================================
def step4_assemble(video_files, audio_path):
    print("\n=== STEP 4: Assemble ===", flush=True)
    
    # Find video file (webp or mp4)
    video_src = None
    for f in video_files:
        if f.endswith('.webp') or f.endswith('.mp4'):
            video_src = f
            break
    
    if not video_src:
        print("  [ERROR] No video file found!", flush=True)
        return None
    
    # Convert webp to mp4
    video_mp4 = os.path.join(OUTPUT_DIR, 'video.mp4')
    final = os.path.join(OUTPUT_DIR, 'final_output.mp4')
    
    if video_src.endswith('.webp'):
        cmd = ['ffmpeg', '-y', '-i', video_src, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', video_mp4]
        print(f"  Converting webp → mp4...", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  [ERROR] webp→mp4: {r.stderr[:300]}", flush=True)
            return None
    else:
        shutil.copy2(video_src, video_mp4)
    
    # Merge with audio
    if audio_path and os.path.exists(audio_path):
        cmd = ['ffmpeg', '-y', '-i', video_mp4, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', final]
        print(f"  Merging audio...", flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            print(f"  [WARN] Audio merge failed, using video only", flush=True)
            shutil.copy2(video_mp4, final)
    else:
        shutil.copy2(video_mp4, final)
    
    if os.path.exists(final):
        size = os.path.getsize(final) / 1024 / 1024
        print(f"  ✅ Final: {final} ({size:.1f}MB)", flush=True)
        return final
    return None

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("VIDEO PIPELINE TEST v2", flush=True)
    print("=" * 60, flush=True)
    t0 = time.time()
    
    keyframe = step1_keyframe()
    if not keyframe:
        print("FATAL: No keyframe!", flush=True)
        sys.exit(1)
    
    video_files = step2_i2v(keyframe)
    if not video_files:
        print("FATAL: No video!", flush=True)
        sys.exit(1)
    
    audio = step3_tts()
    final = step4_assemble(video_files, audio)
    
    elapsed = time.time() - t0
    print(f"\n{'='*60}", flush=True)
    print(f"PIPELINE {'COMPLETE' if final else 'FAILED'} in {elapsed/60:.1f}min", flush=True)
    if final:
        print(f"Output: {final}", flush=True)
    print(f"{'='*60}", flush=True)
