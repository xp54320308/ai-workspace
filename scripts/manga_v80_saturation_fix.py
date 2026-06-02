"""v5 Test: Fix oversaturation with end_image + lower noise_aug_strength"""
import json
import time
import shutil
import urllib.request
from pathlib import Path
try:
    import av
except ImportError:
    av = None

BASE = "http://127.0.0.1:8188"
COMFY_ROOT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI")
INPUT_DIR = COMFY_ROOT / "input"
OUTPUT_DIR = COMFY_ROOT / "output"
RUN_TAG = f"manga5s_v80_saturation_fix_{time.strftime('%Y%m%d_%H%M%S')}"
RUN_DIR = OUTPUT_DIR / RUN_TAG
RUN_DIR.mkdir(parents=True, exist_ok=True)

STYLE_LOCK = (
    "anime manga drama, high quality home room animation, "
    "same young anime girl in navy sailor school uniform, "
    "same quiet home room, stationary wooden window, warm sunset light, "
    "fixed house interior, stable face and outfit, natural indoor motion"
)

NEGATIVE = (
    "train, train carriage, moving vehicle, rushing scenery, fast outside movement, "
    "hard cut, scene change, different room, different girl, different clothes, "
    "identity change, face drift, deformed face, bad hands, extra fingers, "
    "missing fingers, blurry, low quality, overexposed, oversaturated, "
    "text, watermark, logo, frozen background"
)

TEST_SHOT = {
    "prompt": (
        "A visible evening breeze enters the home: sheer curtain billows softly, "
        "her long black hair and sailor ribbon flutter gently, she raises her right hand "
        "to cup her cheek, eyes blink once, sunlight sweeps across her face, "
        "camera makes a small smooth push-in."
    ),
    "seed": 20260508001,
    "cfg": 4.0,
}


def api_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def api_get(path):
    return json.loads(urllib.request.urlopen(f"{BASE}{path}", timeout=30).read())


def wait_for(prompt_id, timeout=1800, poll=5):
    start = time.time()
    while time.time() - start < timeout:
        try:
            hist = api_get(f"/history/{prompt_id}")
            if prompt_id in hist:
                return hist[prompt_id]
        except:
            pass
        time.sleep(poll)
    raise TimeoutError(f"Timeout for {prompt_id}")


def get_output_files(result):
    files = []
    for node_out in result.get("outputs", {}).values():
        for img in node_out.get("images", []):
            files.append(("image", img.get("filename"), img.get("subfolder")))
        for vid in node_out.get("videos", []):
            files.append(("video", vid.get("filename"), vid.get("subfolder")))
        for g in node_out.get("gifs", []):
            files.append(("gif", g.get("filename"), g.get("subfolder")))
    return files


def find_output(filename, subfolder=""):
    if subfolder:
        p = OUTPUT_DIR / subfolder / filename
        return p if p.exists() else None
    for p in OUTPUT_DIR.rglob(filename):
        return p
    return None


def find_recent_output(pattern, after_time):
    for p in sorted(OUTPUT_DIR.rglob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.stat().st_mtime > after_time:
            return p
    return None


def copy_to_input(src_path, new_name):
    dst = INPUT_DIR / new_name
    shutil.copy2(src_path, dst)
    return dst


def extract_last_frame(video_path, shot_id):
    output_path = RUN_DIR / f"{shot_id}_lastframe.png"
    try:
        if av is None:
            raise ImportError("PyAV not installed")
        with av.open(str(video_path)) as container:
            frames = [frame.to_image() for frame in container.decode(video=0)]
            if frames:
                frames[-1].save(str(output_path))
                return output_path
    except Exception as e:
        print(f"  Warning: Could not extract last frame: {e}")
    return None


def run_i2v_with_endframe(shot, start_img_path, end_img_path=None):
    """I2V with both start AND end frame to prevent drift + lower noise_aug."""
    start_name = f"{shot['id']}_start.png"
    copy_to_input(start_img_path, start_name)

    positive = f"{STYLE_LOCK}. {shot['prompt']}"

    # Build WanFirstLastFrameToVideo inputs
    flf_inputs = {
        "positive": ["7", 0],
        "negative": ["8", 0],
        "vae": ["4", 0],
        "start_image": ["9", 0],
        "width": 832,
        "height": 480,
        "length": 81,
        "batch_size": 1,
    }

    # Load end image if provided
    nodes = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": positive}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEGATIVE}},
        "9": {"class_type": "LoadImage", "inputs": {"image": start_name}},
    }

    if end_img_path:
        end_name = f"{shot['id']}_end.png"
        copy_to_input(end_img_path, end_name)
        nodes["10"] = {"class_type": "LoadImage", "inputs": {"image": end_name}}
        flf_inputs["end_image"] = ["10", 0]
        # Lower noise augmentation to reduce oversaturation
        flf_inputs["noise_aug_strength"] = 0.05  # default is much higher

    nodes["11"] = {"class_type": "WanFirstLastFrameToVideo", "inputs": flf_inputs}

    # Dual-stage sampler: high noise (0-11) then low noise (11-22)
    nodes["12"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["5", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["11", 2],
        "add_noise": "enable", "noise_seed": shot["seed"] + 100,
        "steps": 22, "cfg": shot["cfg"], "sampler_name": "euler", "scheduler": "simple",
        "start_at_step": 0, "end_at_step": 11, "return_with_leftover_noise": "enable"
    }}
    nodes["13"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["6", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["12", 0],
        "add_noise": "disable", "noise_seed": 0,
        "steps": 22, "cfg": shot["cfg"], "sampler_name": "euler", "scheduler": "simple",
        "start_at_step": 11, "end_at_step": 10000, "return_with_leftover_noise": "disable"
    }}
    nodes["14"] = {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}}
    nodes["15"] = {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": 16.0}}
    nodes["16"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["15", 0], "filename_prefix": f"{RUN_TAG}/{shot['id']}_raw",
        "format": "mp4", "codec": "h264"
    }}

    start_time = time.time()
    result = wait_for(api_post("/prompt", {"prompt": nodes})["prompt_id"], timeout=1800)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{shot['id']}_raw_*.mp4", start_time)
        if found:
            return found
        raise RuntimeError(f"No video for {shot['id']}")
    return find_output(vid[0][1], vid[0][2])


def generate_end_frame_with_qwen(start_img_path, shot):
    """Use Qwen Image Edit to generate a matching end frame from start frame."""
    ref_str = start_img_path.name if isinstance(start_img_path, Path) else str(start_img_path)
    if isinstance(start_img_path, Path) and start_img_path.parent == RUN_DIR:
        copy_to_input(start_img_path, ref_str)

    end_prompt = (
        f"{shot['prompt']} "
        "Generate the final frame of this animation sequence. "
        "Keep the same character, same room, same lighting. "
        "The character should be in a natural ending pose for this motion."
    )

    prompt = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2509_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": ref_str}},
        "5": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Edit-2509-Multiple-angles.safetensors", "strength_model": 0.8}},
        "6": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["5", 0], "lora_name": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["4", 0], "prompt": end_prompt}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEGATIVE}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 480, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["9", 0], "seed": shot["seed"] + 50, "steps": 4, "cfg": shot["cfg"], "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": f"{RUN_TAG}/endframe_qwen"}}
    }
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"])
    files = get_output_files(result)
    img = [f for f in files if f[0] == "image"][0]
    return find_output(img[1], img[2])


def run_rife(video_path, shot_id):
    input_name = f"{shot_id}_rife.mp4"
    copy_to_input(video_path, input_name)

    prompt = {
        "1": {"class_type": "LoadVideo", "inputs": {"file": input_name}},
        "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
        "3": {"class_type": "RIFE VFI", "inputs": {
            "frames": ["2", 0], "ckpt_name": "rife49.pth", "clear_cache_after_n_frames": 8,
            "multiplier": 2, "fast_mode": True, "ensemble": True, "scale_factor": 1.0,
            "dtype": "float16", "torch_compile": False, "batch_size": 1
        }},
        "4": {"class_type": "VHS_VideoCombine", "inputs": {
            "images": ["3", 0], "frame_rate": 32, "loop_count": 0,
            "filename_prefix": f"{RUN_TAG}/{shot_id}_32fps",
            "format": "video/h264-mp4", "pingpong": False, "save_output": True,
            "pix_fmt": "yuv420p", "crf": 18, "save_metadata": True, "trim_to_audio": False
        }}
    }
    start = time.time()
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=600)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{shot_id}_32fps_*.mp4", start)
        if found:
            return found
        raise RuntimeError(f"No RIFE output for {shot_id}")
    return find_output(vid[0][1], vid[0][2])


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"v80 Saturation Fix Test: {RUN_TAG}")
    print(f"{'='*60}")

    # Use existing start frame from v78 or latest
    start_candidates = sorted(INPUT_DIR.glob("manga5s_v78_*_start.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not start_candidates:
        start_candidates = sorted(INPUT_DIR.glob("manga5s_v*_start.png"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not start_candidates:
        print("ERROR: No start frame found in input/")
        raise SystemExit(1)

    start_frame = start_candidates[0]
    print(f"Using start frame: {start_frame.name}")

    # Test A: I2V with start only (baseline, same as before but lower cfg)
    print(f"\n--- Test A: Start-only, CFG={TEST_SHOT['cfg']} ---")
    raw_a = run_i2v_with_endframe(TEST_SHOT, start_frame)
    print(f"  Raw video: {raw_a.name} ({raw_a.stat().st_size // 1024}KB)")
    rife_a = run_rife(raw_a, f"{TEST_SHOT['id']}_startonly")
    print(f"  RIFE 32fps: {rife_a.name} ({rife_a.stat().st_size // 1024}KB)")

    # Extract last frame from test A
    last_a = extract_last_frame(raw_a, f"{TEST_SHOT['id']}_startonly")

    # Test B: I2V with start + end frame (the fix)
    print(f"\n--- Test B: Start+End frame, CFG={TEST_SHOT['cfg']} ---")
    if last_a:
        raw_b = run_i2v_with_endframe(TEST_SHOT, start_frame, last_a)
        print(f"  Raw video: {raw_b.name} ({raw_b.stat().st_size // 1024}KB)")
        rife_b = run_rife(raw_b, f"{TEST_SHOT['id']}_startend")
        print(f"  RIFE 32fps: {rife_b.name} ({rife_b.stat().st_size // 1024}KB)")
    else:
        # Generate end frame with Qwen Image Edit
        print("  Generating end frame with Qwen Image Edit...")
        end_frame = generate_end_frame_with_qwen(start_frame, TEST_SHOT)
        print(f"  End frame: {end_frame.name}")
        raw_b = run_i2v_with_endframe(TEST_SHOT, start_frame, end_frame)
        print(f"  Raw video: {raw_b.name} ({raw_b.stat().st_size // 1024}KB)")
        rife_b = run_rife(raw_b, f"{TEST_SHOT['id']}_startend")
        print(f"  RIFE 32fps: {rife_b.name} ({rife_b.stat().st_size // 1024}KB)")

    print(f"\n{'='*60}")
    print(f"Test complete! Compare A vs B in: {RUN_DIR}")
    print(f"A = start-only (should still have drift)")
    print(f"B = start+end (should fix drift + saturation)")
    print(f"{'='*60}")
