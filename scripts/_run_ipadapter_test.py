import json, urllib.request, time

COMFYUI_URL = 'http://127.0.0.1:8188'

prompt = {
    '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}},
    '2': {'class_type': 'LoadImage', 'inputs': {'image': 'char_A.png', 'upload': 'image'}},
    '3': {'class_type': 'LoadImage', 'inputs': {'image': 'char_B.png', 'upload': 'image'}},
    '4': {'class_type': 'MaskRectArea', 'inputs': {'x': 0, 'y': 0, 'width': 50, 'height': 100, 'blur_radius': 10}},
    '5': {'class_type': 'MaskRectArea', 'inputs': {'x': 50, 'y': 0, 'width': 50, 'height': 100, 'blur_radius': 10}},
    '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a beautiful young woman with long black hair, wearing a white dress, standing on the left, anime style', 'clip': ['1', 1]}},
    '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a handsome young man with short brown hair, wearing a black leather jacket, standing on the right, anime style', 'clip': ['1', 1]}},
    '8': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'two people standing together in a flower garden, cherry blossoms, sunny day, detailed, high quality, anime illustration', 'clip': ['1', 1]}},
    '9': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, lowres, distorted, deformed, ugly, bad anatomy, text, watermark', 'clip': ['1', 1]}},
    '10': {'class_type': 'IPAdapterRegionalConditioning', 'inputs': {'image': ['2', 0], 'mask': ['4', 0], 'positive': ['6', 0], 'negative': ['9', 0], 'image_weight': 0.8, 'prompt_weight': 1.0, 'weight_type': 'linear', 'start_at': 0.0, 'end_at': 1.0}},
    '11': {'class_type': 'IPAdapterRegionalConditioning', 'inputs': {'image': ['3', 0], 'mask': ['5', 0], 'positive': ['7', 0], 'negative': ['9', 0], 'image_weight': 0.8, 'prompt_weight': 1.0, 'weight_type': 'linear', 'start_at': 0.0, 'end_at': 1.0}},
    '12': {'class_type': 'IPAdapterCombineParams', 'inputs': {'params_1': ['10', 0], 'params_2': ['11', 0]}},
    '13': {'class_type': 'ConditioningCombineMultiple+', 'inputs': {'conditioning_1': ['10', 1], 'conditioning_2': ['11', 1], 'conditioning_3': ['8', 0]}},
    '14': {'class_type': 'ConditioningCombineMultiple+', 'inputs': {'conditioning_1': ['10', 2], 'conditioning_2': ['11', 2], 'conditioning_3': ['9', 0]}},
    '15': {'class_type': 'IPAdapterUnifiedLoader', 'inputs': {'model': ['1', 0], 'preset': 'PLUS (high strength)'}},
    '16': {'class_type': 'IPAdapterFromParams', 'inputs': {'model': ['15', 0], 'ipadapter': ['15', 1], 'ipadapter_params': ['12', 0], 'combine_embeds': 'concat', 'embeds_scaling': 'V only'}},
    '17': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
    '18': {'class_type': 'KSampler', 'inputs': {'model': ['16', 0], 'positive': ['13', 0], 'negative': ['14', 0], 'latent_image': ['17', 0], 'seed': 42, 'control_after_generate': 'fixed', 'steps': 30, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m_sde', 'scheduler': 'karras', 'denoise': 1.0}},
    '19': {'class_type': 'VAEDecode', 'inputs': {'samples': ['18', 0], 'vae': ['1', 2]}},
    '20': {'class_type': 'SaveImage', 'inputs': {'images': ['19', 0], 'filename_prefix': 'ipadapter_2chars'}}
}

data = json.dumps({'prompt': prompt}).encode()
req = urllib.request.Request(f'{COMFYUI_URL}/prompt', data=data, headers={'Content-Type': 'application/json'}, method='POST')
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    prompt_id = result.get('prompt_id')
    print(f'Queued: {prompt_id}')

    while True:
        resp = urllib.request.urlopen(f'{COMFYUI_URL}/history/{prompt_id}')
        history = json.loads(resp.read())
        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get('status', {})
            if status.get('status_str') == 'error':
                msgs = status.get('messages', [])
                for m in msgs:
                    if m[0] == 'execution_error':
                        msg = m[1].get('exception_message', '?')
                        print(f'ERROR: {msg}')
                break
            elif status.get('completed'):
                outputs = entry.get('outputs', {})
                for nid, out in outputs.items():
                    if 'images' in out:
                        for img in out['images']:
                            fn = img.get('filename', '?')
                            print(f'Output: {fn}')
                break
        time.sleep(3)
        print('.', end='', flush=True)

    print('Done!')
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'HTTP {e.code}: {body}')
