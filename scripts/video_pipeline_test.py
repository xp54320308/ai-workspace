"""
端到端视频制作流水线测试
流程: 关键帧(HiDream) → 视频(Wan 2.2 I2V 5B) → 语音(EdgeTTS) → 合成(FFmpeg)
"""
import json
import urllib.request
import time
import subprocess
import os
import sys

WORKSPACE = r'C:\Users\qw\.openclaw\workspace'
OUTPUT_DIR = os.path.join(WORKSPACE, 'pipeline_test')
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMFYUI_URL = 'http://127.0.0.1:8188'

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
            print(f"  [{label}] [{i*10}s] Error: {e}", flush=True)
        time.sleep(10)
    print(f"  [{label}] TIMEOUT!", flush=True)
    return None

def get_output_images(outputs, node_id="9"):
    imgs = []
    if node_id in outputs:
        for img in outputs[node_id].get("images", []):
            src = os.path.join(r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output', img["filename"])
            dst = os.path.join(OUTPUT_DIR, img["filename"])
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, dst)
                imgs.append(dst)
                print(f"  Copied: {img['filename']}", flush=True)
    return imgs

# ============================================================
# STEP 1: Generate Keyframe with HiDream
# ============================================================
def step1_keyframe():
    print("\n=== STEP 1: Generate Keyframe (HiDream) ===", flush=True)
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "hidream_i1_full_fp8.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "llama_3.1_8b_instruct_fp8_scaled.safetensors", "type": "hidream"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "a beautiful sunset over a calm ocean, golden light reflecting on gentle waves, silhouette of a sailing boat in the distance, seagulls flying, cinematic wide shot, warm orange and purple sky, photorealistic, 8k masterpiece", "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry, low quality, ugly, distorted", "clip": ["2", 0]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 480, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 42, "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "pipeline_keyframe"}}
    }
    pid = submit_workflow(wf, "keyframe")
    outputs = wait_for_prompt(pid, "keyframe", timeout_min=5)
    if not outputs:
        return None
    imgs = get_output_images(outputs)
    return imgs[0] if imgs else None

# ============================================================
# STEP 2: Image to Video with Wan 2.2 I2V 5B
# ============================================================
def step2_image_to_video(keyframe_path):
    print("\n=== STEP 2: Image to Video (Wan 2.2 I2V 5B) ===", flush=True)
    # Copy keyframe to ComfyUI input directory
    import shutil
    input_dir = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input'
    input_filename = 'pipeline_keyframe.png'
    input_path = os.path.join(input_dir, input_filename)
    shutil.copy2(keyframe_path, input_path)
    print(f"  Keyframe copied to: {input_path}", flush=True)
    
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": input_filename}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "smooth camera slowly panning right, gentle waves moving, seagulls flying across the sky, warm golden light, cinematic", "clip": ["2", 0]}},
        "6": {"class_type": "WanImageToVideo", "inputs": {
            "model": ["1", 0],
            "clip_vision": ["4", 0],
            "vae": ["3", 0],
            "positive": ["5", 0],
            "width": 832,
            "height": 480,
            "length": 81,
            "batch_size": 1
        }},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["6", 0],
            "seed": 123,
            "steps": 30,
            "cfg": 6.0,
            "sampler_name": "uni_pc",
            "scheduler": "simple",
            "positive": ["6", 1],
            "negative": ["6", 2],
            "latent_image": ["6", 3],
            "denoise": 1.0
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "pipeline_video_frame"}}
    }
    pid = submit_workflow(wf, "i2v")
    outputs = wait_for_prompt(pid, "i2v", timeout_min=10)
    if not outputs:
        return None
    imgs = get_output_images(outputs)
    return imgs

# ============================================================
# STEP 3: Generate TTS Audio with EdgeTTS
# ============================================================
def step3_tts():
    print("\n=== STEP 3: Generate TTS Audio (EdgeTTS) ===", flush=True)
    text = "A beautiful sunset over the ocean. Golden light reflects on gentle waves as a sailing boat glides across the horizon."
    output_path = os.path.join(OUTPUT_DIR, 'narration.mp3')
    
    try:
        # Try edge-tts CLI
        cmd = ['edge-tts', '--voice', 'en-US-AriaNeural', '--text', text, '--write-media', output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"  TTS generated: {output_path}", flush=True)
            return output_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback: use Python edge_tts module
    try:
        import edge_tts
        import asyncio
        async def gen():
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(output_path)
        asyncio.run(gen())
        if os.path.exists(output_path):
            print(f"  TTS generated (module): {output_path}", flush=True)
            return output_path
    except ImportError:
        pass
    
    print("  [WARN] edge-tts not available, skipping TTS", flush=True)
    return None

# ============================================================
# STEP 4: Assemble Video with FFmpeg
# ============================================================
def step4_assemble(frames, audio_path):
    print("\n=== STEP 4: Assemble Video (FFmpeg) ===", flush=True)
    
    # Sort frames by filename
    frames.sort()
    if not frames:
        print("  [ERROR] No frames!", flush=True)
        return None
    
    # Create frame list file
    frame_list = os.path.join(OUTPUT_DIR, 'frames.txt')
    with open(frame_list, 'w') as f:
        for frame in frames:
            f.write(f"file '{frame}'\n")
            f.write("duration 0.0333\n")  # ~30fps
    
    video_only = os.path.join(OUTPUT_DIR, 'video_only.mp4')
    final_video = os.path.join(OUTPUT_DIR, 'final_output.mp4')
    
    # Step 4a: frames → video
    cmd1 = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', frame_list,
        '-vf', 'scale=832:480:flags=lanczos',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
        '-pix_fmt', 'yuv420p',
        video_only
    ]
    print(f"  Running: {' '.join(cmd1[:6])}...", flush=True)
    r1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=120)
    if r1.returncode != 0:
        print(f"  [ERROR] FFmpeg frames→video: {r1.stderr[:500]}", flush=True)
        # Try alternative: use image sequence directly
        cmd1alt = [
            'ffmpeg', '-y', '-framerate', '30',
            '-i', os.path.join(OUTPUT_DIR, 'pipeline_video_frame_%05d_.png'),
            '-vf', 'scale=832:480:flags=lanczos',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-pix_fmt', 'yuv420p',
            video_only
        ]
        print(f"  Trying alternative...", flush=True)
        r1 = subprocess.run(cmd1alt, capture_output=True, text=True, timeout=120)
        if r1.returncode != 0:
            print(f"  [ERROR] Alt also failed: {r1.stderr[:500]}", flush=True)
            return None
    
    print(f"  Video created: {video_only}", flush=True)
    
    # Step 4b: merge video + audio (or just copy if no audio)
    if audio_path and os.path.exists(audio_path):
        cmd2 = [
            'ffmpeg', '-y',
            '-i', video_only,
            '-i', audio_path,
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            final_video
        ]
        print(f"  Merging audio...", flush=True)
        r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        if r2.returncode != 0:
            print(f"  [WARN] Audio merge failed, using video only: {r2.stderr[:300]}", flush=True)
            import shutil
            shutil.copy2(video_only, final_video)
    else:
        import shutil
        shutil.copy2(video_only, final_video)
    
    if os.path.exists(final_video):
        size_mb = os.path.getsize(final_video) / 1024 / 1024
        print(f"  ✅ Final video: {final_video} ({size_mb:.1f}MB)", flush=True)
        return final_video
    return None

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("VIDEO PRODUCTION PIPELINE TEST", flush=True)
    print("=" * 60, flush=True)
    
    t0 = time.time()
    
    # Step 1: Keyframe
    keyframe = step1_keyframe()
    if not keyframe:
        print("FATAL: Keyframe generation failed!", flush=True)
        sys.exit(1)
    print(f"  Keyframe: {keyframe}", flush=True)
    
    # Step 2: I2V
    frames = step2_image_to_video(keyframe)
    if not frames:
        print("FATAL: Video generation failed!", flush=True)
        sys.exit(1)
    print(f"  Frames: {len(frames)}", flush=True)
    
    # Step 3: TTS
    audio = step3_tts()
    
    # Step 4: Assemble
    final = step4_assemble(frames, audio)
    
    elapsed = time.time() - t0
    print(f"\n{'=' * 60}", flush=True)
    print(f"PIPELINE COMPLETE in {elapsed:.0f}s ({elapsed/60:.1f}min)", flush=True)
    if final:
        print(f"Output: {final}", flush=True)
    else:
        print("FAILED - check errors above", flush=True)
    print(f"{'=' * 60}", flush=True)
