import json, urllib.request, time

COMFYUI_URL = 'http://127.0.0.1:8188'

# Generate character A: young woman portrait
prompt_a = {
    '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}},
    '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a beautiful young woman with long flowing black hair, blue eyes, wearing a white summer dress, portrait, upper body, soft lighting, anime style, detailed face, looking at viewer', 'clip': ['1', 1]}},
    '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, lowres, bad anatomy, distorted, ugly, multiple people, full body', 'clip': ['1', 1]}},
    '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
    '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0], 'seed': 100, 'steps': 25, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m_sde', 'scheduler': 'karras', 'denoise': 1.0}},
    '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
    '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'char_portrait_A'}}
}

# Generate character B: young man portrait
prompt_b = {
    '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}},
    '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a handsome young man with short spiky brown hair, green eyes, wearing a black leather jacket, portrait, upper body, dramatic lighting, anime style, detailed face, looking at viewer', 'clip': ['1', 1]}},
    '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, lowres, bad anatomy, distorted, ugly, multiple people, full body', 'clip': ['1', 1]}},
    '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
    '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0], 'seed': 200, 'steps': 25, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m_sde', 'scheduler': 'karras', 'denoise': 1.0}},
    '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
    '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'char_portrait_B'}}
}

for name, p in [('A', prompt_a), ('B', prompt_b)]:
    data = json.dumps({'prompt': p}).encode()
    req = urllib.request.Request(f'{COMFYUI_URL}/prompt', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    pid = result.get('prompt_id')
    print(f'Character {name} queued: {pid}')

    while True:
        resp = urllib.request.urlopen(f'{COMFYUI_URL}/history/{pid}')
        history = json.loads(resp.read())
        if pid in history:
            status = history[pid].get('status', {})
            if status.get('status_str') == 'error':
                for m in status.get('messages', []):
                    if m[0] == 'execution_error':
                        print(f'ERROR: {m[1].get("exception_message", "?")}')
                break
            elif status.get('completed'):
                outputs = history[pid].get('outputs', {})
                for nid, out in outputs.items():
                    if 'images' in out:
                        for img in out['images']:
                            print(f'Output: {img.get("filename", "?")}')
                break
        time.sleep(2)
        print('.', end='', flush=True)
    print()

print('Both characters generated!')
