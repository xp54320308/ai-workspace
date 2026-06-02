import json, urllib.request, time

COMFYUI_URL = 'http://127.0.0.1:8188'

# Quick test: single character to verify pipeline works
prompt = {
    '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}},
    '2': {'class_type': 'LoadImage', 'inputs': {'image': 'portrait_A.png', 'upload': 'image'}},
    '3': {'class_type': 'LoadImage', 'inputs': {'image': 'portrait_B.png', 'upload': 'image'}},
    '4': {'class_type': 'MaskRectArea', 'inputs': {'x': 0, 'y': 0, 'width': 45, 'height': 100, 'blur_radius': 5}},
    '5': {'class_type': 'MaskRectArea', 'inputs': {'x': 55, 'y': 0, 'width': 45, 'height': 100, 'blur_radius': 5}},
    '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a beautiful young woman with long flowing black hair, blue eyes, white flower hair accessory, white off-shoulder dress with lace trim, silver earrings, standing on the left, anime style', 'clip': ['1', 1]}},
    '8': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a handsome young man with spiky brown hair, green eyes, black leather jacket with silver studs, green shirt, silver chain necklace, standing on the right, anime style', 'clip': ['1', 1]}},
    '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, lowres, distorted, deformed, ugly, bad anatomy, extra limbs, extra fingers, text, watermark, signature, cross-eyed, asymmetric eyes', 'clip': ['1', 1]}},
    '10': {'class_type': 'IPAdapterRegionalConditioning', 'inputs': {
        'image': ['2', 0], 'mask': ['4', 0], 'positive': ['6', 0], 'negative': ['7', 0],
        'image_weight': 1.2, 'prompt_weight': 1.0, 'weight_type': 'ease out',
        'start_at': 0.0, 'end_at': 1.0
    }},
    '11': {'class_type': 'IPAdapterRegionalConditioning', 'inputs': {
        'image': ['3', 0], 'mask': ['5', 0], 'positive': ['8', 0], 'negative': ['7', 0],
        'image_weight': 1.2, 'prompt_weight': 1.0, 'weight_type': 'ease out',
        'start_at': 0.0, 'end_at': 1.0
    }},
    '12': {'class_type': 'IPAdapterCombineParams', 'inputs': {'params_1': ['10', 0], 'params_2': ['11', 0]}},
    # Use ConditioningCombine (2 inputs only) - same as v2 which worked
    '13': {'class_type': 'ConditioningCombine', 'inputs': {'conditioning_1': ['10', 1], 'conditioning_2': ['11', 1]}},
    '14': {'class_type': 'ConditioningCombine', 'inputs': {'conditioning_1': ['10', 2], 'conditioning_2': ['11', 2]}},
    '15': {'class_type': 'IPAdapterUnifiedLoader', 'inputs': {'model': ['1', 0], 'preset': 'PLUS (high strength)'}},
    '16': {'class_type': 'IPAdapterFromParams', 'inputs': {
        'model': ['15', 0], 'ipadapter': ['15', 1], 'ipadapter_params': ['12', 0],
        'combine_embeds': 'concat', 'embeds_scaling': 'V only'
    }},
    '17': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
    '18': {'class_type': 'KSampler', 'inputs': {
        'model': ['16', 0], 'positive': ['13', 0], 'negative': ['14', 0], 'latent_image': ['17', 0],
        'seed': 100, 'steps': 30, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m_sde', 'scheduler': 'karras', 'denoise': 1.0
    }},
    '19': {'class_type': 'VAEDecode', 'inputs': {'samples': ['18', 0], 'vae': ['1', 2]}},
    '20': {'class_type': 'SaveImage', 'inputs': {'images': ['19', 0], 'filename_prefix': 'ipa4_test'}}
}

data = json.dumps({'prompt': prompt}).encode()
req = urllib.request.Request(f'{COMFYUI_URL}/prompt', data=data, headers={'Content-Type': 'application/json'}, method='POST')
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
pid = result.get('prompt_id')
print(f'Queued: {pid}')

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
    time.sleep(3)
    print('.', end='', flush=True)

print('\nDone!')
