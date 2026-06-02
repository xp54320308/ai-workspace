import json, urllib.request, urllib.error, time

COMFYUI_URL = 'http://127.0.0.1:8188'

prompt = {
    # Load Wan 2.2 I2V model
    '1': {'class_type': 'WanVideoModelLoader', 'inputs': {
        'model': 'wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',
        'base_precision': 'fp16',
        'quantization': 'fp8_e4m3fn_scaled',
        'load_device': 'offload_device'
    }},
    # Load T5 text encoder
    '2': {'class_type': 'LoadWanVideoT5TextEncoder', 'inputs': {
        'model_name': 'umt5_xxl_fp16.safetensors',
        'precision': 'bf16'
    }},
    # Load Wan VAE
    '3': {'class_type': 'WanVideoVAELoader', 'inputs': {
        'model_name': 'wan2.2_vae.safetensors',
        'precision': 'bf16'
    }},
    # Load best IP-Adapter result
    '4': {'class_type': 'LoadImage', 'inputs': {
        'image': 'ipa5_eout_12_kv.png',
        'upload': 'image'
    }},
    # Load CLIP vision
    '6': {'class_type': 'CLIPVisionLoader', 'inputs': {
        'clip_name': 'clip_vision_h.safetensors'
    }},
    # Encode text prompts
    '5': {'class_type': 'WanVideoTextEncode', 'inputs': {
        'positive_prompt': 'two anime characters standing together, the woman with long flowing black hair and blue eyes in a white off-shoulder dress gently turns her head, the man with spiky brown hair and green eyes in a black leather jacket smiles warmly, smooth slow camera dolly forward, gentle wind blowing hair, anime style, high quality, cinematic lighting',
        'negative_prompt': 'blurry, distorted, deformed, ugly, bad anatomy, static, no movement, watermark, text',
        't5': ['2', 0],
        'force_offload': True
    }},
    # Encode reference image with CLIP vision
    '7': {'class_type': 'WanVideoClipVisionEncode', 'inputs': {
        'clip_vision': ['6', 0],
        'image_1': ['4', 0],
        'strength_1': 1.0,
        'strength_2': 1.0,
        'crop': 'disabled',
        'combine_embeds': 'concat',
        'force_offload': True
    }},
    # Create I2V latent
    '8': {'class_type': 'WanVideoImageToVideoEncode', 'inputs': {
        'width': 832,
        'height': 480,
        'num_frames': 81,
        'noise_aug_strength': 0.0,
        'start_latent_strength': 1.0,
        'end_latent_strength': 1.0,
        'force_offload': True,
        'vae': ['3', 0],
        'clip_embeds': ['7', 0],
        'start_image': ['4', 0]
    }},
    # Sample
    '9': {'class_type': 'WanVideoSampler', 'inputs': {
        'model': ['1', 0],
        'image_embeds': ['8', 0],
        'text_embeds': ['5', 0],
        'steps': 30,
        'cfg': 6.0,
        'shift': 5.0,
        'seed': 42,
        'force_offload': True,
        'scheduler': 'unipc',
        'riflex_freq_index': 0
    }},
    # Decode to frames
    '10': {'class_type': 'WanVideoDecode', 'inputs': {
        'vae': ['3', 0],
        'samples': ['9', 0],
        'enable_vae_tiling': True,
        'tile_x': 272,
        'tile_y': 272,
        'tile_stride_x': 144,
        'tile_stride_y': 128
    }},
    # Save video
    '11': {'class_type': 'VHS_VideoCombine', 'inputs': {
        'images': ['10', 0],
        'frame_rate': 8,
        'loop_count': 0,
        'filename_prefix': 'wan_i2v_test',
        'format': 'video/h264-mp4',
        'pingpong': False,
        'save_output': True
    }}
}

data = json.dumps({'prompt': prompt}).encode()
req = urllib.request.Request(f'{COMFYUI_URL}/prompt', data=data, headers={'Content-Type': 'application/json'}, method='POST')
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    pid = result.get('prompt_id')
    print(f'Wan I2V queued: {pid}')
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'Error {e.code}: {body[:2000]}')
    exit(1)

while True:
    try:
        resp = urllib.request.urlopen(f'{COMFYUI_URL}/history/{pid}')
        history = json.loads(resp.read())
        if pid in history:
            status = history[pid].get('status', {})
            if status.get('status_str') == 'error':
                for m in status.get('messages', []):
                    if m[0] == 'execution_error':
                        print(f'ERROR: {m[1].get("exception_message", "?")}')
                        print(f'Node: {m[1].get("node_id", "?")}')
                break
            elif status.get('completed'):
                outputs = history[pid].get('outputs', {})
                for nid, out in outputs.items():
                    if 'gifs' in out:
                        for v in out['gifs']:
                            print(f'Video: {v.get("filename", "?")}')
                    elif 'images' in out:
                        for img in out['images']:
                            print(f'Image: {img.get("filename", "?")}')
                break
    except Exception as e:
        print(f'Poll error: {e}')
    time.sleep(10)
    print('.', end='', flush=True)

print('\nDone!')
