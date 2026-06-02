import json, urllib.request, urllib.error, time

COMFYUI_URL = 'http://127.0.0.1:8188'

prompt = {
    # Load KJ HIGH model (from example workflow)
    '1': {'class_type': 'WanVideoModelLoader', 'inputs': {
        'model': r'WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors',
        'base_precision': 'fp16_fast',
        'quantization': 'fp8_e4m3fn_scaled',
        'load_device': 'offload_device'
    }},
    # T5 text encoder
    '2': {'class_type': 'LoadWanVideoT5TextEncoder', 'inputs': {
        'model_name': 'umt5-xxl-enc-bf16.safetensors',
        'precision': 'bf16'
    }},
    # Wan 2.1 VAE (as used in example)
    '3': {'class_type': 'WanVideoVAELoader', 'inputs': {
        'model_name': 'wan_2.1_vae.safetensors',
        'precision': 'bf16'
    }},
    # Reference image
    '4': {'class_type': 'LoadImage', 'inputs': {
        'image': 'ipa5_eout_12_kv.png',
        'upload': 'image'
    }},
    # Text encode
    '5': {'class_type': 'WanVideoTextEncode', 'inputs': {
        'positive_prompt': 'two anime characters, the woman with black hair and blue eyes in white dress gently turns her head, the man with brown hair and green eyes in black jacket smiles, smooth camera movement, anime style',
        'negative_prompt': 'blurry, distorted, deformed, ugly, bad anatomy, static, watermark, text',
        't5': ['2', 0],
        'force_offload': True
    }},
    # CLIP vision
    '6': {'class_type': 'CLIPVisionLoader', 'inputs': {
        'clip_name': 'clip_vision_h.safetensors'
    }},
    # CLIP vision encode
    '7': {'class_type': 'WanVideoClipVisionEncode', 'inputs': {
        'clip_vision': ['6', 0],
        'image_1': ['4', 0],
        'strength_1': 1.0,
        'strength_2': 1.0,
        'crop': 'disabled',
        'combine_embeds': 'concat',
        'force_offload': True
    }},
    # I2V encode
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
    # Sampler
    '9': {'class_type': 'WanVideoSampler', 'inputs': {
        'model': ['1', 0],
        'image_embeds': ['8', 0],
        'text_embeds': ['5', 0],
        'steps': 30,
        'cfg': 6.0,
        'shift': 8.0,
        'seed': 42,
        'force_offload': True,
        'scheduler': 'dpm++_sde',
        'riflex_freq_index': 0
    }},
    # Decode
    '10': {'class_type': 'WanVideoDecode', 'inputs': {
        'vae': ['3', 0],
        'samples': ['9', 0],
        'enable_vae_tiling': True,
        'tile_x': 272,
        'tile_y': 272,
        'tile_stride_x': 144,
        'tile_stride_y': 128
    }},
    # Save
    '11': {'class_type': 'VHS_VideoCombine', 'inputs': {
        'images': ['10', 0],
        'frame_rate': 16,
        'loop_count': 0,
        'filename_prefix': 'wan_i2v_v3',
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
    print('Queued:', pid)
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print('Error %d: %s' % (e.code, body[:2000]))
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
                        msg = m[1].get('exception_message', '?')
                        node = m[1].get('node_id', '?')
                        print('ERROR at node %s: %s' % (node, msg))
                break
            elif status.get('completed'):
                outputs = history[pid].get('outputs', {})
                for nid, out in outputs.items():
                    if 'gifs' in out:
                        for v in out['gifs']:
                            print('Video:', v.get('filename', '?'))
                    elif 'images' in out:
                        for img in out['images']:
                            print('Image:', img.get('filename', '?'))
                break
    except Exception as e:
        print('Poll error:', e)
    time.sleep(15)
    print('.', end='', flush=True)
print()
