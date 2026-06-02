"""v80 Test: Fix oversaturation - A/B comparison
Test A: Start-only I2V (baseline, current pipeline)
Test B: Start+End I2V with end_image
Test C: Start+End + lower CFG
"""
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
RUN_TAG = f"manga5s_v80_{time.strftime('%Y%m%d_%H%M%S')}"
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

SHOT_PROMPT = (
    "A visible evening breeze enters the home: sheer curtain billows softly, "
    "her long black hair and sailor ribbon flutter gently, she raises her right hand "
    "to cup her cheek, eyes blink once, sunlight sweeps across her face, "
    "camera makes a small smooth push-in."
)


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
        print(f"  Warning: {e}")
    return None


def build_i2v_nodes(shot_id, prompt_text, seed, cfg, start_name, end_name=None):
    """Build I2V node graph. If end_name provided, use start+end frame mode."""
    nodes = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": f"{STYLE_LOCK}. {prompt_text}"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEGATIVE}},
        "9": {"class_type": "LoadImage", "inputs": {"image": start_name}},
    }

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

    if end_name:
        nodes["10"] = {"class_type": "LoadImage", "inputs": {"image": end_name}}
        flf_inputs["end_image"] = ["10", 0]

    nodes["11"] = {"class_type": "WanFirstLastFrameToVideo", "inputs": flf_inputs}
    nodes["12"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["5", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["11", 2],
        "add_noise": "enable", "noise_seed": seed + 100,
        "steps": 22, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
        "start_at_step": 0, "end_at_step": 11, "return_with_leftover_noise": "enable"
    }}
    nodes["13"] = {"class_type": "KSamplerAdvanced", "inputs": {
        "model": ["6", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["12", 0],
        "add_noise": "disable", "noise_seed": 0,
        "steps": 22, "cfg": cfg, "sampler_name": "euler", "scheduler": "simple",
        "start_at_step": 11, "end_at_step": 10000, "return_with_leftover_noise": "disable"
    }}
    nodes["14"] = {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}}
    nodes["15"] = {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": 16.0}}
    nodes["16"] = {"class_type": "SaveVideo", "inputs": {
        "video": ["15", 0], "filename_prefix": f"{RUN_TAG}/{shot_id}",
        "format": "mp4", "codec": "h264"
    }}
    return nodes


def run_i2v(shot_id, prompt_text, seed, cfg, start_img_path, end_img_path=None):
    start_name = f"{shot_id}_start.png"
    copy_to_input(start_img_path, start_name)

    end_name = None
    if end_img_path:
        end_name = f"{shot_id}_end.png"
        copy_to_input(end_img_path, end_name)

    nodes = build_i2v_nodes(shot_id, prompt_text, seed, cfg, start_name, end_name)
    start_time = time.time()
    result = wait_for(api_post("/prompt", {"prompt": nodes})["prompt_id"], timeout=1800)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{shot_id}_*.mp4", start_time)
        if found:
            return found
        raise RuntimeError(f"No video for {shot_id}")
    return find_output(vid[0][1], vid[0][2])


def run_rife(video_path, tag):
    input_name = f"{tag}_rife.mp4"
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
            "filename_prefix": f"{RUN_TAG}/{tag}_32fps",
            "format": "video/h264-mp4", "pingpong": False, "save_output": True,
            "pix_fmt": "yuv420p", "crf": 18, "save_metadata": True, "trim_to_audio": False
        }}
    }
    start = time.time()
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=600)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{tag}_32fps_*.mp4", start)
        if found:
            return found
        raise RuntimeError(f"No RIFE for {tag}")
    return find_output(vid[0][1], vid[0][2])


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"v80 Saturation Fix A/B Test: {RUN_TAG}")
    print(f"{'='*60}")

    # Find a good start frame
    start_candidates = sorted(INPUT_DIR.glob("manga5s_v78_*_start.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not start_candidates:
        start_candidates = sorted(INPUT_DIR.glob("manga5s_v*_start.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not start_candidates:
        print("ERROR: No start frame found")
        raise SystemExit(1)

    start_frame = start_candidates[0]
    print(f"Start frame: {start_frame.name}")

    seed = 20260508001

    # ── Test A: Start-only, CFG=4.0 (baseline) ──
    print(f"\n--- Test A: start-only, CFG=4.0 ---")
    raw_a = run_i2v("testA_startonly_cfg4", SHOT_PROMPT, seed, 4.0, start_frame)
    print(f"  raw: {raw_a.name} ({raw_a.stat().st_size // 1024}KB)")
    rife_a = run_rife(raw_a, "testA")
    print(f"  32fps: {rife_a.name} ({rife_a.stat().st_size // 1024}KB)")

    # Extract last frame from A
    last_a = extract_last_frame(raw_a, "testA")

    if last_a:
        # ── Test B: Start+End, CFG=4.0 ──
        print(f"\n--- Test B: start+end, CFG=4.0 ---")
        raw_b = run_i2v("testB_startend_cfg4", SHOT_PROMPT, seed + 10, 4.0, start_frame, last_a)
        print(f"  raw: {raw_b.name} ({raw_b.stat().st_size // 1024}KB)")
        rife_b = run_rife(raw_b, "testB")
        print(f"  32fps: {rife_b.name} ({rife_b.stat().st_size // 1024}KB)")

        # ── Test C: Start+End, CFG=3.0 ──
        print(f"\n--- Test C: start+end, CFG=3.0 ---")
        raw_c = run_i2v("testC_startend_cfg3", SHOT_PROMPT, seed + 20, 3.0, start_frame, last_a)
        print(f"  raw: {raw_c.name} ({raw_c.stat().st_size // 1024}KB)")
        rife_c = run_rife(raw_c, "testC")
        print(f"  32fps: {rife_c.name} ({rife_c.stat().st_size // 1024}KB)")

        # ── Test D: Start+End, CFG=2.5 ──
        print(f"\n--- Test D: start+end, CFG=2.5 ---")
        raw_d = run_i2v("testD_startend_cfg25", SHOT_PROMPT, seed + 30, 2.5, start_frame, last_a)
        print(f"  raw: {raw_d.name} ({raw_d.stat().st_size // 1024}KB)")
        rife_d = run_rife(raw_d, "testD")
        print(f"  32fps: {rife_d.name} ({rife_d.stat().st_size // 1024}KB)")

    print(f"\n{'='*60}")
    print(f"Done! Compare in: {RUN_DIR}")
    print(f"A = start-only CFG4 (baseline, likely oversaturated)")
    print(f"B = start+end CFG4 (end_image should reduce drift)")
    print(f"C = start+end CFG3 (lower CFG = less saturation)")
    print(f"D = start+end CFG2.5 (even lower)")
    print(f"{'='*60}")
