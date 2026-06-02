import json, urllib.request, urllib.error, sys, time, shutil, os

INPUT_IMAGE = "ipa5_eout_12_kv.png"
PROMPT = "two anime characters standing together in a sunlit garden, wind gently blowing their hair, cherry blossom petals floating, cinematic lighting, smooth camera movement"
NEG_PROMPT = "static, jitter, flickering, distortion, low quality"
WIDTH, HEIGHT = 832, 480
FRAMES = 81
STEPS = 6
CFG = 6.0
SHIFT = 8.0
SPLIT_STEP = 3

# Copy input image
src = os.path.join(r"C:\Users\qw\.openclaw\workspace", INPUT_IMAGE)
dst = os.path.join(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input", INPUT_IMAGE)
shutil.copy2(src, dst)

workflow = {
    # T5 text encoder
    "11": {"class_type": "LoadWanVideoT5TextEncoder", "inputs": {
        "model_name": "umt5_xxl_fp16.safetensors",
        "precision": "bf16"}},
    # Text encode
    "16": {"class_type": "WanVideoTextEncode", "inputs": {
        "positive_prompt": PROMPT,
        "negative_prompt": NEG_PROMPT,
        "t5": ["11", 0],
        "force_offload": True}},
    # HIGH model (first stage)
    "22": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16",
        "quantization": "disabled",
        "load_device": "offload_device"}},
    # LOW model (second stage)
    "71": {"class_type": "WanVideoModelLoader", "inputs": {
        "model": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "base_precision": "bf16",
        "quantization": "disabled",
        "load_device": "offload_device"}},
    # VAE
    "38": {"class_type": "WanVideoVAELoader", "inputs": {
        "model_name": "wan_2.1_vae.safetensors", "precision": "bf16"}},
    # Load image
    "67": {"class_type": "LoadImage", "inputs": {
        "image": INPUT_IMAGE}},
    # Image to video encode
    "89": {"class_type": "WanVideoImageToVideoEncode", "inputs": {
        "width": WIDTH, "height": HEIGHT, "num_frames": FRAMES,
        "noise_aug_strength": 0.0, "start_latent_strength": 1.0,
        "end_latent_strength": 1.0, "force_offload": True,
        "fun_or_fl2v_model": False, "tiled_vae": False,
        "vae": ["38", 0], "start_image": ["67", 0]}},
    # First stage sampler (HIGH model, partial steps)
    "27": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["22", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "steps": STEPS, "cfg": CFG, "shift": SHIFT, "seed": 42,
        "force_offload": True, "scheduler": "dpm++_sde",
        "riflex_freq_index": 0, "start_step": 0, "end_step": SPLIT_STEP}},
    # Second stage sampler (LOW model, remaining steps)
    "90": {"class_type": "WanVideoSampler", "inputs": {
        "model": ["71", 0], "image_embeds": ["89", 0], "text_embeds": ["16", 0],
        "samples": ["27", 0],
        "steps": STEPS, "cfg": CFG, "shift": SHIFT, "seed": 42,
        "force_offload": True, "scheduler": "dpm++_sde",
        "riflex_freq_index": 0, "start_step": SPLIT_STEP, "end_step": -1}},
    # Decode
    "28": {"class_type": "WanVideoDecode", "inputs": {
        "vae": ["38", 0], "samples": ["90", 0],
        "enable_vae_tiling": True,
        "tile_x": 272, "tile_y": 272,
        "tile_stride_x": 144, "tile_stride_y": 128}},
    # Video output
    "60": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["28", 0], "frame_rate": 8, "loop_count": 0,
        "filename_prefix": "wan_i2v", "format": "video/h264-mp4",
        "pix_fmt": "yuv420p", "crf": 19, "save_metadata": True,
        "trim_to_audio": False, "pingpong": False, "save_output": True}}
}

data = json.dumps({"prompt": workflow}).encode()
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data)
try:
    result = json.loads(urllib.request.urlopen(req).read())
    pid = result['prompt_id']
    print(f"Queued: {pid}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body[:3000]}")
    sys.exit(1)

for i in range(120):
    time.sleep(10)
    h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:8188/history/{pid}").read())
    if pid in h:
        status = h[pid].get('status', {})
        if status.get('completed'):
            print("Done!")
            for nid, n in h[pid].get('outputs', {}).items():
                if 'gifs' in n:
                    for g in n['gifs']:
                        print(f"  Video: {g.get('filename')} subfolder={g.get('subfolder','')}")
            break
        elif status.get('status_str') == 'error':
            msgs = status.get('messages', [])
            for m in msgs:
                if isinstance(m, list) and len(m) >= 2 and m[0] == 'execution_error':
                    print(f"ERROR: {m[1].get('exception_message','')}")
                    print(f"  Node: {m[1].get('node_id')}")
                    print(f"  Traceback: {m[1].get('traceback','')[:500]}")
            break
else:
    print("Timeout after 20 min")
