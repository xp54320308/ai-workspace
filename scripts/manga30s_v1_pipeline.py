"""Manga 30s Pipeline v1: 6-shot storyboard -> T2I -> I2V -> RIFE -> Stitch"""
import json
import time
import shutil
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
COMFY_ROOT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI")
INPUT_DIR = COMFY_ROOT / "input"
OUTPUT_DIR = COMFY_ROOT / "output"
RUN_TAG = f"manga30s_v1_{time.strftime('%Y%m%d_%H%M%S')}"
RUN_DIR = OUTPUT_DIR / RUN_TAG
RUN_DIR.mkdir(parents=True, exist_ok=True)

# ── Storyboard: 6 shots, 5 seconds each ──
SHOTS = [
    {
        "id": "shot01_window",
        "time": "0-5s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, a young girl with long black hair in navy sailor uniform seated beside a wooden window, side profile, looking at wutong tree outside, dusk orange light, sheer white curtain, quiet room, warm healing color grading, delicate line art",
        "i2v_positive": "anime manga drama, same girl by the wooden window, evening breeze enters, sheer curtain billows inward, her long black hair flutters with inertia, she slowly raises her right hand to cup her cheek, eyes blink once, sunlight sweeps across her face, outside tree leaves sway, camera makes a small smooth push-in, stable identity",
        "seed": 20260507301,
    },
    {
        "id": "shot02_gaze_down",
        "time": "5-10s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, same young girl with long black hair in navy sailor uniform, she slowly turns her head down toward a wooden desk, drooping eyes, gentle eyelashes, dusk indoor light, curtain half floating, warm healing color grading",
        "i2v_positive": "continue in the same room, she slowly turns her head, her gaze lowers toward the desk, eyelashes and hair move subtly, curtain keeps fluttering, warm dusk light remains consistent, camera tilts down only a little, stable identity, stable face",
        "seed": 20260507302,
    },
    {
        "id": "shot03_letter_touch",
        "time": "10-15s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, close-up of girl's delicate fingertips touching vintage yellowed letter paper on wooden desktop, warm dusk light, soft shadow, retro texture, same navy sailor uniform sleeve visible",
        "i2v_positive": "slow downward camera movement from upper body to hand close-up, fingertips approach then gently touch the edge of the old letter paper, warm light and shadow softly slide over the desktop, gentle breathing motion, stable hand anatomy",
        "seed": 20260507303,
    },
    {
        "id": "shot04_paper_wind",
        "time": "15-20s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, letter paper on wooden desktop, girl's fingertip lightly resting, one paper corner lifted by wind, white curtain blurred in background, warm dusk ambient light",
        "i2v_positive": "fixed camera, evening wind enters the room, the corner of the letter paper lifts and curls softly, curtain in background flutters, warm indoor ambient light breathes gently, small dust motes float in sunbeam, stable composition",
        "seed": 20260507304,
    },
    {
        "id": "shot05_look_up",
        "time": "20-25s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, same girl looking up slowly from letter paper toward sunset glow outside the window, orange pink sky, wutong leaves swaying, warm light on her face, navy sailor uniform",
        "i2v_positive": "camera slowly moves upward from the letter paper to her face, she raises her eyes and head toward the window, sunset orange pink glow increases, wutong leaves sway outside, hair moves softly, emotional gentle moment, stable identity",
        "seed": 20260507305,
    },
    {
        "id": "shot06_ending",
        "time": "25-30s",
        "t2i_prompt": "masterpiece, best quality, anime style, soft painting, cinematic 16:9, wide shot, same girl by the wooden window looking at sunset sky, wutong tree outside, white curtain fluttering, full quiet room composition, warm golden hour light, navy sailor uniform",
        "i2v_positive": "slow zoom out, camera pulls back from the girl to a full wide window scene, sunset fills the sky, curtain and hair flutter softly, warm halo and haze close the story gently, peaceful ending, stable identity, stable scene",
        "seed": 20260507306,
    },
]

T2I_NEGATIVE = "low quality, blurry, bad anatomy, extra fingers, watermark, text, ugly, deformed, different person, different clothes"
I2V_NEGATIVE = "still image, frozen background, weak motion, identity change, different girl, face drift, deformed face, extra fingers, bad anatomy, blurry, low quality, watermark, text, hard scene cut"


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
    # Fallback: scan output directory for recent files
    if not files:
        for p in sorted(OUTPUT_DIR.rglob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.stat().st_mtime > time.time() - 120:
                files.append(("video", p.name, p.parent.name))
                break
        for p in sorted(OUTPUT_DIR.rglob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.stat().st_mtime > time.time() - 120:
                files.append(("image", p.name, p.parent.name))
                break
    return files


def find_output(filename, subfolder=""):
    if subfolder:
        p = OUTPUT_DIR / subfolder / filename
        return p if p.exists() else None
    for p in OUTPUT_DIR.rglob(filename):
        return p
    return None


def copy_to_input(src_path, new_name):
    dst = INPUT_DIR / new_name
    shutil.copy2(src_path, dst)
    return dst


def run_t2i(shot):
    prompt = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "anything-v5-PrtRE.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": shot["t2i_prompt"]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": T2I_NEGATIVE}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 480, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0], "seed": shot["seed"], "steps": 25, "cfg": 7.5, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"images": ["6", 0], "filename_prefix": f"{RUN_TAG}/{shot['id']}_frame"}}
    }
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"])
    files = get_output_files(result)
    img = [f for f in files if f[0] == "image"][0]
    return find_output(img[1], img[2])


def run_i2v(shot, start_img_path):
    input_name = f"{shot['id']}_start.png"
    copy_to_input(start_img_path, input_name)

    prompt = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["2", 0], "shift": 8.0}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": shot["i2v_positive"]}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": I2V_NEGATIVE}},
        "9": {"class_type": "LoadImage", "inputs": {"image": input_name}},
        "11": {"class_type": "WanFirstLastFrameToVideo", "inputs": {"positive": ["7", 0], "negative": ["8", 0], "vae": ["4", 0], "start_image": ["9", 0], "width": 832, "height": 480, "length": 81, "batch_size": 1}},
        "12": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["5", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["11", 2], "add_noise": "enable", "noise_seed": shot["seed"] + 100, "steps": 22, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": 11, "return_with_leftover_noise": "enable"}},
        "13": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["6", 0], "positive": ["11", 0], "negative": ["11", 1], "latent_image": ["12", 0], "add_noise": "disable", "noise_seed": 0, "steps": 22, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "start_at_step": 11, "end_at_step": 10000, "return_with_leftover_noise": "disable"}},
        "14": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["4", 0]}},
        "15": {"class_type": "CreateVideo", "inputs": {"images": ["14", 0], "fps": 16.0}},
        "16": {"class_type": "SaveVideo", "inputs": {"video": ["15", 0], "filename_prefix": f"{RUN_TAG}/{shot['id']}_raw", "format": "mp4", "codec": "h264"}}
    }
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=1800)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")]
    if not vid:
        # Fallback: search output dir for the raw video
        pattern = f"{shot['id']}_raw_*.mp4"
        for p in sorted(OUTPUT_DIR.rglob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
            return p
        raise RuntimeError(f"No video output found for {shot['id']}")
    return find_output(vid[0][1], vid[0][2])


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
    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=600)
    files = get_output_files(result)
    vid = [f for f in files if f[0] in ("video", "gif")][0]
    return find_output(vid[1], vid[2])


def stitch_videos(video_paths, output_name):
    """Concatenate videos using ComfyUI LoadVideo + ImageBatch + CreateVideo"""
    # Build a chain of LoadVideo + GetVideoComponents + ImageBatch nodes
    nodes = {}
    links = []
    link_id = 1
    node_id = 1

    # Load and extract frames from each video
    frame_outputs = []
    for i, vpath in enumerate(video_paths):
        input_name = f"stitch_input_{i}.mp4"
        copy_to_input(vpath, input_name)

        nodes[str(node_id)] = {"class_type": "LoadVideo", "inputs": {"file": input_name}}
        load_id = node_id
        node_id += 1

        nodes[str(node_id)] = {"class_type": "GetVideoComponents", "inputs": {"video": [str(load_id), 0]}}
        get_id = node_id
        node_id += 1

        links.append([link_id, load_id, 0, get_id, 0, "VIDEO"])
        link_id += 1
        frame_outputs.append((get_id, 0))

    # Chain ImageBatch nodes to concatenate all frames
    current_input = frame_outputs[0]
    for i in range(1, len(frame_outputs)):
        nodes[str(node_id)] = {"class_type": "ImageBatch", "inputs": {"image1": [str(current_input[0]), current_input[1]], "image2": [str(frame_outputs[i][0]), frame_outputs[i][1]]}}
        links.append([link_id, current_input[0], current_input[1], node_id, 0, "IMAGE"])
        link_id += 1
        links.append([link_id, frame_outputs[i][0], frame_outputs[i][1], node_id, 1, "IMAGE"])
        link_id += 1
        current_input = (node_id, 0)
        node_id += 1

    # Create and save final video
    nodes[str(node_id)] = {"class_type": "CreateVideo", "inputs": {"images": [str(current_input[0]), current_input[1]], "fps": 32.0}}
    links.append([link_id, current_input[0], current_input[1], node_id, 0, "IMAGE"])
    link_id += 1
    create_id = node_id
    node_id += 1

    nodes[str(node_id)] = {"class_type": "SaveVideo", "inputs": {"video": [str(create_id), 0], "filename_prefix": f"{RUN_TAG}/{output_name}", "format": "mp4", "codec": "h264"}}
    links.append([link_id, create_id, 0, node_id, 0, "VIDEO"])

    prompt = {}
    for nid, n in nodes.items():
        prompt[nid] = n

    result = wait_for(api_post("/prompt", {"prompt": prompt})["prompt_id"], timeout=600)
    files = get_output_files(result)
    vid = [f for f in files if f[0] == "video"][0]
    return find_output(vid[1], vid[2])


# ── Main Pipeline ──
if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Manga 30s Pipeline: {RUN_TAG}")
    print(f"{'='*60}")

    final_videos = []

    for shot in SHOTS:
        print(f"\n--- {shot['id']} ({shot['time']}) ---")

        # T2I
        print(f"  [T2I] Generating start frame...")
        start_img = run_t2i(shot)
        print(f"  -> {start_img.name} ({start_img.stat().st_size // 1024}KB)")

        # I2V
        print(f"  [I2V] Generating video...")
        raw_video = run_i2v(shot, start_img)
        print(f"  -> {raw_video.name} ({raw_video.stat().st_size // 1024}KB)")

        # RIFE
        print(f"  [RIFE] Interpolating to 32fps...")
        final_32fps = run_rife(raw_video, shot["id"])
        print(f"  -> {final_32fps.name} ({final_32fps.stat().st_size // 1024}KB)")

        final_videos.append(final_32fps)

    # Stitch all shots
    print(f"\n--- Stitching {len(final_videos)} shots ---")
    final = stitch_videos(final_videos, "final_30s_manga")
    print(f"  -> {final.name} ({final.stat().st_size // 1024}KB)")

    print(f"\n{'='*60}")
    print(f"Pipeline complete!")
    print(f"Output directory: {RUN_DIR}")
    print(f"Final video: {final}")
    print(f"{'='*60}")
