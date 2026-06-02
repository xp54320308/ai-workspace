"""Manga 30s Pipeline v2: Character-consistent with Qwen Image Edit + Chained I2V"""
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
RUN_TAG = f"manga30s_v2_{time.strftime('%Y%m%d_%H%M%S')}"
RUN_DIR = OUTPUT_DIR / RUN_TAG
RUN_DIR.mkdir(parents=True, exist_ok=True)

# ── Character definition (locked) ──
CHARACTER_REF = "aki_story_ref.png"  # Must exist in input/
CHARACTER_DESC = "young anime girl with long black hair and amber eyes, navy sailor school uniform"

STYLE_LOCK = (
    "anime manga drama, high quality home room animation, "
    "same young anime girl in navy sailor school uniform, "
    "same quiet home room, stationary wooden window, warm sunset light, "
    "fixed house interior, stable face and outfit, natural indoor motion, "
    "living environment, no scene cut"
)

NEGATIVE = (
    "train, train carriage, moving vehicle, rushing scenery, fast outside movement, "
    "hard cut, scene change, different room, different girl, different clothes, "
    "identity change, face drift, deformed face, bad hands, extra fingers, "
    "missing fingers, duplicate person, blurry, low quality, overexposed, "
    "oversaturated, text, watermark, logo, frozen background"
)

# ── 6 shots with chained continuity ──
SHOTS = [
    {
        "id": "01_wind_hand_cheek",
        "prompt": (
            "A visible evening breeze enters the home: sheer curtain billows and rolls inward in soft waves, "
            "her long black hair and sailor ribbon flutter with clear inertia, she raises her right hand "
            "from chest level to cup her cheek and gently brushes hair near her eye, eyes blink once, "
            "sunlight and tree-leaf shadows sweep across her face and chair, outside tree leaves sway gently, "
            "camera makes a small smooth push-in."
        ),
        "seed": 20260507901,
        "cfg": 5.5,
    },
    {
        "id": "02_gaze_down_desk",
        "prompt": (
            "Continue in the same home room. Her hand slowly lowers from her cheek, her gaze drops "
            "toward the wooden desk, upper body leans forward slightly, hair settles then sways again "
            "with the breeze, curtain continues soft waves, sunlight moves gently over the wall and floor, "
            "camera tilts down only a little."
        ),
        "seed": 20260507902,
        "cfg": 5.35,
    },
    {
        "id": "03_reach_letter",
        "prompt": (
            "Continue naturally. Camera eases lower toward the desk but keeps part of the girl in frame, "
            "her right hand reaches toward a vintage yellowed letter paper on the wooden desk, "
            "fingers approach the paper edge, hair tips sway near her shoulder, "
            "curtain and warm light keep moving softly."
        ),
        "seed": 20260507903,
        "cfg": 5.45,
    },
    {
        "id": "04_paper_wind",
        "prompt": (
            "A slightly stronger indoor breeze lifts one corner of the vintage letter paper and curls it upward, "
            "her fingertips react near the paper, curtain billows behind her in the same room, "
            "small dust motes float in the sunbeam, tree-leaf shadows ripple on the desk and chair, "
            "no outside rushing."
        ),
        "seed": 20260507904,
        "cfg": 5.45,
    },
    {
        "id": "05_look_up_sunset",
        "prompt": (
            "She slowly raises her head from the letter and looks toward the sunset outside the fixed window, "
            "warm orange light brightens her eyes and cheek, hair and sailor ribbon sway softly, "
            "curtain drifts back, outside leaves sway gently in place and clouds drift very slowly."
        ),
        "seed": 20260507905,
        "cfg": 5.35,
    },
    {
        "id": "06_soft_ending",
        "prompt": (
            "A calm ending shot. Camera slowly eases back a little while staying in the same home room, "
            "the girl remains by the wooden window, curtain floats, hair moves softly, "
            "sunset haze fills the window, room shadows breathe gently across the chair and wall, "
            "peaceful but not frozen."
        ),
        "seed": 20260507906,
        "cfg": 5.2,
    },
]


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


def generate_keyframe(shot, ref_image):
    """Generate keyframe using Qwen Image Edit with character reference."""
    # Ensure ref_image is a string filename
    if isinstance(ref_image, Path):
        # If it's in the RUN_DIR, copy to input and use filename
        ref_str = ref_image.name
        if ref_image.parent == RUN_DIR:
            copy_to_input(ref_image, ref_str)
    else:
        ref_str = str(ref_image)
    prompt = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2509_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": ref_str}},
        "5": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "Qwen-Edit-2509-Multiple-angles.safetensors", "strength_model": 0.8}},
        "6": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["5", 0], "lora_name": "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors", "strength_model": 1.0}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["4", 0], "prompt": f"{CHARACTER_DESC}. {shot['prompt']}"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEGATIVE}},
        "9": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 480, "batch_size": 1}},
        "10": {"class_type": "KSampler", "inputs": {"model": ["6", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["9", 0], "seed": shot["seed"], "steps": 4, "cfg": shot["cfg"], "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "11": {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}},
        "12": {"class_type": "SaveImage", "inputs": {"images": ["11", 0], "filename_prefix": f"{RUN_TAG}/{shot['id']}_keyframe"}}
    }
    start = time.time()
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"])
    files = get_output_files(result)
    img = [f for f in files if f[0] == "image"][0]
    return find_output(img[1], img[2])


def run_i2v_chained(shot, start_img_path):
    """Generate I2V video from start frame with consistent style."""
    input_name = f"{shot['id']}_start.png"
    copy_to_input(start_img_path, input_name)

    positive = f"{STYLE_LOCK}. {shot['prompt']}"

    prompt = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": positive}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEGATIVE}},
        "9": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "11": {"class_type": "WanFirstLastFrameToVideo", "inputs": {"positive": ["7", 0], "negative": ["8", 0], "vae": ["4", 0], "start_image": ["9", 0], "width": 832, "height": 480, "length": 81, "batch_size": 1}},
        "12": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["5", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["11", 2], "add_noise": "enable", "noise_seed": shot["seed"] + 100, "steps": 22, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": 11, "return_with_leftover_noise": "enable"}},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["6", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["12", 0], "add_noise": "disable", "noise_seed": 0, "steps": 22, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 11, "end_at_step": 10000, "return_with_leftover_noise": "disable"}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}},
        "15": {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": 16.0}},
        "16": {"class_type": "SaveVideo", "inputs": {"video": ["15", 0], "filename_prefix": f"{RUN_TAG}/{shot['id']}_raw", "format": "mp4", "codec": "h264"}}
    }
    start = time.time()
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=1800)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{shot['id']}_raw_*.mp4", start)
        if found:
            return found
        raise RuntimeError(f"No video for {shot['id']}")
    return find_output(vid[0][1], vid[0][2])


def extract_last_frame(video_path, shot_id):
    """Extract last frame from video using PyAV."""
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


def stitch_videos(video_paths, output_name):
    nodes = {}
    link_id = 1
    node_id = 1
    frame_outputs = []

    for i, vpath in enumerate(video_paths):
        input_name = f"stitch_{i}.mp4"
        copy_to_input(vpath, input_name)
        nodes[str(node_id)] = {"class_type": "LoadVideo", "inputs": {"file": input_name}}
        load_id = node_id
        node_id += 1
        nodes[str(node_id)] = {"class_type": "GetVideoComponents", "inputs": {"video": [str(load_id), 0]}}
        get_id = node_id
        node_id += 1
        frame_outputs.append((get_id, 0))

    current = frame_outputs[0]
    for i in range(1, len(frame_outputs)):
        nodes[str(node_id)] = {"class_type": "ImageBatch", "inputs": {"image1": [str(current[0]), current[1]], "image2": [str(frame_outputs[i][0]), frame_outputs[i][1]]}}
        current = (node_id, 0)
        node_id += 1

    nodes[str(node_id)] = {"class_type": "CreateVideo", "inputs": {"images": [str(current[0]), current[1]], "fps": 32.0}}
    create_id = node_id
    node_id += 1
    nodes[str(node_id)] = {"class_type": "SaveVideo", "inputs": {"video": [str(create_id), 0], "filename_prefix": f"{RUN_TAG}/{output_name}", "format": "mp4", "codec": "h264"}}

    start = time.time()
    result = wait_for(api_post("/prompt", {"prompt": nodes})["prompt_id"], timeout=600)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        found = find_recent_output(f"{output_name}_*.mp4", start)
        if found:
            return found
        raise RuntimeError("No stitch output")
    return find_output(vid[0][1], vid[0][2])


# ── Main Pipeline ──
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Manga 30s v2 (Character Consistent): {RUN_TAG}")
    print(f"{'='*60}")

    # Prepare reference image
    ref_path = INPUT_DIR / CHARACTER_REF
    if not ref_path.exists():
        print(f"ERROR: Reference image not found: {ref_path}")
        print(f"Please place a character reference image at: {INPUT_DIR / CHARACTER_REF}")
        raise SystemExit(1)

    final_videos = []
    prev_end_frame = None

    for i, shot in enumerate(SHOTS):
        print(f"\n--- {shot['id']} ---")

        # Step 1: Generate keyframe with Qwen Image Edit (character consistent)
        print(f"  [Keyframe] Generating with Qwen Image Edit + LoRA...")
        if prev_end_frame:
            # Use previous shot's last frame as reference for continuity
            ref_for_shot = prev_end_frame
        else:
            ref_for_shot = CHARACTER_REF
        keyframe = generate_keyframe(shot, ref_for_shot)
        print(f"  -> {keyframe.name} ({keyframe.stat().st_size // 1024}KB)")

        # Step 2: I2V from keyframe
        print(f"  [I2V] Generating video...")
        raw_video = run_i2v_chained(shot, keyframe)
        print(f"  -> {raw_video.name} ({raw_video.stat().st_size // 1024}KB)")

        # Step 3: RIFE to 32fps
        print(f"  [RIFE] Interpolating...")
        final_32fps = run_rife(raw_video, shot["id"])
        print(f"  -> {final_32fps.name} ({final_32fps.stat().st_size // 1024}KB)")

        final_videos.append(final_32fps)

        # Step 4: Extract last frame for chaining
        print(f"  [Chain] Extracting last frame for next shot...")
        last_frame = extract_last_frame(raw_video, shot["id"])
        if last_frame:
            prev_end_frame = last_frame
            print(f"  -> {last_frame.name}")
        else:
            prev_end_frame = keyframe
            print(f"  -> Using keyframe as fallback")

    # Stitch all shots
    print(f"\n--- Stitching {len(final_videos)} shots ---")
    final = stitch_videos(final_videos, "final_30s_manga")
    print(f"  -> {final.name} ({final.stat().st_size // 1024}KB)")

    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"Output: {RUN_DIR}")
    print(f"Final: {final}")
    print(f"{'='*60}")
