import json, urllib.request, urllib.error, time

COMFYUI_URL = 'http://127.0.0.1:8188'

# Try native ComfyUI Wan pipeline (not WanVideoWrapper)
prompt = {
    # Load model with native UNETLoader
    '1': {'class_type': 'UNETLoader', 'inputs': {
        'unet_name': 'wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',
        'weight_dtype': 'default'
    }},
    # Load T5 text encoder
    '2': {'class_type': 'CLIPLoader', 'inputs': {
        'clip_name': 'umt5_xxl_fp16.safetensors',
        'type': 'wan'
    }},
    # Load Wan VAE with native VAELoader
    '3': {'class_type': 'VAELoader', 'inputs': {
        'vae_name': 'wan2.2_vae.safetensors'
    }},
    # Load reference image
    '4': {'class_type': 'LoadImage', 'inputs': {
        'image': 'ipa5_eout_12_kv.png',
        'upload': 'image'
    }},
    # Encode positive text
    '5': {'class_type': 'CLIPTextEncode', 'inputs': {
        'text': 'two anime characters, the woman with black hair and blue eyes in white dress gently turns her head, the man with brown hair and green eyes in black jacket smiles, smooth camera movement, anime style',
        'clip': ['2', 0]
    }},
    # Encode negative text
    '6': {'class_type': 'CLIPTextEncode', 'inputs': {
        'text': 'blurry, distorted, deformed, ugly, bad anatomy, static, watermark, text',
        'clip': ['2', 0]
    }},
    # CLIP vision for image conditioning
    '7': {'class_type': 'CLIPVisionLoader', 'inputs': {
        'clip_name': 'clip_vision_h.safetensors'
    }},
    # WanImageToVideo creates the latent + conditioning from image
    '8': {'class_type': 'WanImageToVideo', 'inputs': {
        'clip_vision_output': ['9', 0],
        'positive': ['5', 0],
        'negative': ['6', 0],
        'vae': ['3', 0],
        'width': 832,
        'height': 480,
        'length': 81,
        'batch_size': 1,
        'start_image': ['4', 0]
    }},
    # CLIP Vision Encode
    '9': {'class_type': 'CLIPVisionEncode', 'inputs': {
        'clip_vision': ['7', 0],
        'image': ['4', 0],
        'crop': 'center'
    }},
    # Sample
    '10': {'class_type': 'KSampler', 'inputs': {
        'model': ['1', 0],
        'positive': ['8', 0],
        'negative': ['8', 1],
        'latent_image': ['8', 2],
        'seed': 42,
        'steps': 30,
        'cfg': 5.0,
        'sampler_name': 'uni_pc',
        'scheduler': 'normal',
        'denoise': 1.0
    }},
    # Decode
    '11': {'class_type': 'VAEDecode', 'inputs': {
        'samples': ['10', 0],
        'vae': ['3', 0]
    }},
    # Save via VHS
    '12': {'class_type': 'VHS_VideoCombine', 'inputs': {
        'images': ['11', 0],
        'frame_rate': 8,
        'loop_count': 0,
        'filename_prefix': 'wan_native_i2v',
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
