"""
测试 4: 可复用 Pipeline
输入角色图 → 自动出视频
封装成函数，方便以后调用
"""
import urllib.request, json, time, os, shutil
from dataclasses import dataclass
from typing import Optional

COMFYUI = "http://127.0.0.1:8188"
OUTPUT_DIR = r"C:\Users\qw\.openclaw\workspace"
COMFYUI_OUTPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output"
COMFYUI_INPUT = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input"

def queue_prompt(w, cid="pipeline"):
    data = json.dumps({"prompt": w, "client_id": cid}).encode()
    req = urllib.request.Request(COMFYUI + "/prompt", data=data,
        headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req).read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print(f"  QUEUE ERROR: {e.read().decode()}")
        raise

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

@dataclass
class Character:
    name: str
    image: str  # filename in ComfyUI/input
    prompt: str  # appearance description
    mask_x: int = 0
    mask_y: int = 0
    mask_w: int = 45
    mask_h: int = 100

@dataclass
class VideoConfig:
    motion_prompt: str
    negative_prompt: str = "static, no motion, stiff, low quality, blurry"
    width: int = 832
    height: int = 480
    num_frames: int = 81
    steps: int = 20
    cfg: float = 5.0
    shift: float = 8.0
    seed: int = 42
    start_latent_strength: float = 0.9
    fps: float = 8.0

def generate_ipadapter_frame(characters: list[Character], 
                              output_name: str = "pipeline_frame",
                              width: int = 1024, height: int = 576,
                              steps: int = 30, cfg: float = 7.0,
                              seed: int = 42) -> Optional[str]:
    """Step 1: Generate multi-character frame using IP-Adapter Regional"""
    print(f"  Generating frame with {len(characters)} characters...")
    
    nodes = {}
    neg_text = "lowres, bad anatomy, bad hands, text, error, missing fingers, cropped, worst quality, low quality, blurry, deformed, watermark"
    
    # Base model
    nodes["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}}
    
    # IP-Adapter setup
    nodes["7"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "ipadapter_sd15_model.safetensors"}}
    nodes["10"] = {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}}
    
    # Negative
    nodes["3"] = {"class_type": "CLIPTextEncode", "inputs": {"text": neg_text, "clip": ["1", 1]}}
    
    # Build per-character nodes
    prev_model_out = ["1", 0]
    conditionings = []
    
    for i, char in enumerate(characters):
        img_id = f"img_{i}"
        mask_id = f"mask_{i}"
        pos_id = f"pos_{i}"
        ip_id = f"ip_{i}"
        
        nodes[img_id] = {"class_type": "LoadImage", "inputs": {"image": char.image}}
        nodes[mask_id] = {"class_type": "MaskRectArea", "inputs": {
            "x": char.mask_x, "y": char.mask_y, 
            "width": char.mask_w, "height": char.mask_h, 
            "blur_radius": 5
        }}
        nodes[pos_id] = {"class_type": "CLIPTextEncode", "inputs": {
            "text": char.prompt, "clip": ["1", 1]
        }}
        nodes[ip_id] = {"class_type": "IPAdapterAdvanced", "inputs": {
            "model": prev_model_out, "ipadapter": ["10", 0], "image": [img_id, 0],
            "weight": 1.2, "weight_type": "ease out",
            "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
            "embeds_scaling": "K+V w/ C penalty",
            "attn_mask": [mask_id, 0], "clip_vision": ["7", 0]
        }}
        
        prev_model_out = [ip_id, 0]
        conditionings.append([pos_id, 0])
    
    # Combine conditionings
    if len(conditionings) == 1:
        nodes["cond"] = {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": conditionings[0], "conditioning_2": conditionings[0]
        }}
    else:
        nodes["cond"] = {"class_type": "ConditioningCombine", "inputs": {
            "conditioning_1": conditionings[0], "conditioning_2": conditionings[1]
        }}
        for i in range(2, len(conditionings)):
            prev = "cond"
            new_id = f"cond_{i}"
            nodes[new_id] = {"class_type": "ConditioningCombine", "inputs": {
                "conditioning_1": [prev, 0], "conditioning_2": conditionings[i]
            }}
    
    if len(conditionings) <= 2:
        cond_out = "cond"
    else:
        cond_out = f"cond_{len(conditionings)-1}"
    
    # Generate
    nodes["latent"] = {"class_type": "EmptyLatentImage", "inputs": {
        "width": width, "height": height, "batch_size": 1
    }}
    nodes["sampler"] = {"class_type": "KSampler", "inputs": {
        "model": prev_model_out, "positive": [cond_out, 0], "negative": ["3", 0],
        "latent_image": ["latent", 0],
        "seed": seed, "steps": steps, "cfg": cfg,
        "sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "denoise": 1.0
    }}
    nodes["decode"] = {"class_type": "VAEDecode", "inputs": {"samples": ["sampler", 0], "vae": ["1", 2]}}
    nodes["save"] = {"class_type": "SaveImage", "inputs": {"images": ["decode", 0], "filename_prefix": output_name}}
    
    pid = queue_prompt(nodes, f"pipeline_frame_{output_name}")
    result = wait(pid, timeout=600)
    if not result:
        return None
    
    for nid, out in result["outputs"].items():
        if "images" in out:
            for img in out["images"]:
                fname = img["filename"]
                if img.get("subfolder"):
                    fname = os.path.join(img["subfolder"], fname)
                src = os.path.join(COMFYUI_OUTPUT, fname)
                dst = os.path.join(COMFYUI_INPUT, f"{output_name}.png")
                shutil.copy2(src, dst)
                shutil.copy2(src, os.path.join(OUTPUT_DIR, f"{output_name}.png"))
                return f"{output_name}.png"
    return None


def generate_video(frame_image: str, config: VideoConfig,
                   output_name: str = "pipeline_video",
                   use_twostage: bool = True) -> Optional[str]:
    """Step 2: Generate video from frame using Wan Video I2V"""
    print(f"  Generating video ({config.num_frames} frames, {config.width}x{config.height})...")
    
    nodes = {}
    
    # T5 encoder
    nodes["11"] = {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors", "precision": "bf16"
    }}
    nodes["16"] = {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": config.motion_prompt,
        "negative_prompt": config.negative_prompt,
        "t5": ["11", 0]
    }}
    
    # Models - always load HIGH, optionally LOW for two-stage
    nodes["22"] = {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
    }}
    
    if use_twostage:
        nodes["71"] = {"class_type": "WanVideoModelLoader", "inputs": {
            "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
            "base_precision": "bf16", "quantization": "disabled", "load_device": "offload_device"
        }}
    
    nodes["38"] = {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan_2.1_vae.safetensors", "precision": "bf16"
    }}
    nodes["66"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}}
    nodes["67"] = {"class_type": "LoadImage", "inputs": {"image": frame_image}}
    nodes["68"] = {"class_type": "WanVideoClipVisionEncode", "inputs": {
        "clip_vision": ["66", 0], "image_1": ["67", 0],
        "strength_1": 1.0, "strength_2": 1.0,
        "crop": "center", "combine_embeds": "concat", "force_offload": True
    }}
    nodes["89"] = {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": config.width, "height": config.height, "num_frames": config.num_frames,
        "noise_aug_strength": 0.02, "start_latent_strength": config.start_latent_strength,
        "end_latent_strength": 1.0, "force_offload": True,
        "vae": ["38", 0], "clip_embeds": ["68", 0], "start_image": ["67", 0],
        "fun_or_fl2v_model": False, "tiled_vae": False
    }}
    
    split_step = config.steps // 2
    
    if use_twostage:
        nodes["27"] = {"class_type": "WanVideoSampler", "inputs": {
            "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
            "steps": config.steps, "cfg": config.cfg, "shift": config.shift, "seed": config.seed,
            "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
            "start_step": 0, "end_step": split_step
        }}
        nodes["90"] = {"class_type": "WanVideoSampler", "inputs": {
            "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
            "steps": config.steps, "cfg": config.cfg, "shift": config.shift, "seed": config.seed,
            "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
            "samples": ["27", 0], "start_step": split_step, "end_step": -1
        }}
        decode_input = ["90", 0]
    else:
        nodes["27"] = {"class_type": "WanVideoSampler", "inputs": {
            "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
            "steps": config.steps, "cfg": config.cfg, "shift": config.shift, "seed": config.seed,
            "scheduler": "dpm++_sde", "riflex_freq_index": 0, "force_offload": True,
            "start_step": 0, "end_step": -1
        }}
        decode_input = ["27", 0]
    
    nodes["28"] = {"class_type": "WanVideoDecode", "inputs": {
        "samples": decode_input, "vae": ["38", 0],
        "enable_vae_tiling": True,
        "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128
    }}
    nodes["60"] = {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": config.fps, "loop_count": 0,
        "filename_prefix": output_name,
        "format": "video/h264-mp4", "pingpong": False, "save_output": True
    }}
    
    cid = f"pipeline_vid_{output_name}"
    pid = queue_prompt(nodes, cid)
    result = wait(pid, timeout=1800)
    if not result:
        return None
    
    for nid, out in result["outputs"].items():
        if "gifs" in out:
            for v in out["gifs"]:
                fname = v["filename"]
                if v.get("subfolder"):
                    fname = os.path.join(v["subfolder"], fname)
                src = os.path.join(COMFYUI_OUTPUT, fname)
                dst = os.path.join(OUTPUT_DIR, f"{output_name}.mp4")
                shutil.copy2(src, dst)
                return dst
    return None


# ============================================================
# Demo: Run the full pipeline
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("VIDEO GENERATION PIPELINE")
    print("=" * 60)
    
    # Define characters
    char_a = Character(
        name="Girl A",
        image="portrait_A.png",
        prompt="beautiful young woman with long black hair, blue eyes, white dress, silver earrings, anime style, dynamic pose",
        mask_x=0, mask_y=0, mask_w=45, mask_h=100
    )
    char_b = Character(
        name="Girl B", 
        image="portrait_B.png",
        prompt="young woman with pink hair, green eyes, black outfit, energetic pose, anime style",
        mask_x=55, mask_y=0, mask_w=45, mask_h=100
    )
    
    # Step 1: Generate frame
    print("\n[STEP 1] Generating multi-character frame...")
    frame = generate_ipadapter_frame(
        characters=[char_a, char_b],
        output_name="pipeline_demo_frame",
        width=1024, height=576
    )
    if not frame:
        print("Frame generation FAILED!")
        exit(1)
    print(f"  Frame: {frame}")
    
    # Step 2: Generate video
    print("\n[STEP 2] Generating video...")
    video_config = VideoConfig(
        motion_prompt="cinematic anime scene, two characters on cherry blossom street, gentle breeze, hair flowing, camera pan right, warm golden hour lighting",
        num_frames=81,
        steps=20,
        shift=8.0,
        start_latent_strength=0.9
    )
    video = generate_video(
        frame_image=frame,
        config=video_config,
        output_name="pipeline_demo_video",
        use_twostage=True
    )
    if not video:
        print("Video generation FAILED!")
        exit(1)
    
    print(f"\n{'=' * 60}")
    print(f"PIPELINE COMPLETE!")
    print(f"Frame: {os.path.join(OUTPUT_DIR, frame)}")
    print(f"Video: {video}")
    print(f"Size: {os.path.getsize(video)/1024/1024:.1f} MB")
    print(f"{'=' * 60}")
