import urllib.request, json

prompt = {
    '1': {'class_type': 'CheckpointLoaderKJ', 'inputs': {
        'ckpt_name': 'ltx-2-19b-dev-fp8.safetensors',
        'weight_dtype': 'default',
        'compute_dtype': 'default',
        'patch_cublaslinear': False,
        'sage_attention': 'disabled',
        'enable_fp16_accumulation': False
    }},
    '10': {'class_type': 'LTXAVTextEncoderLoader', 'inputs': {
        'text_encoder': 'gemma_3_12B_it_fp4_mixed.safetensors',
        'ckpt_name': 'ltx-2-19b-dev-fp8.safetensors',
        'device': 'default'
    }},
    '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'a woman walking on beach, cinematic', 'clip': ['10', 0]}},
    '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'blurry, distorted', 'clip': ['10', 0]}},
    '4': {'class_type': 'LTXVConditioning', 'inputs': {'positive': ['2', 0], 'negative': ['3', 0], 'frame_rate': 25.0}},
    '5': {'class_type': 'LoadImage', 'inputs': {'image': 'char_A.png'}},
    '6': {'class_type': 'LTXVImgToVideo', 'inputs': {
        'positive': ['4', 0], 'negative': ['4', 1], 'vae': ['1', 2],
        'image': ['5', 0], 'width': 768, 'height': 512, 'length': 97, 'batch_size': 1, 'strength': 0.7
    }},
    '7': {'class_type': 'KSampler', 'inputs': {
        'model': ['1', 0], 'positive': ['6', 0], 'negative': ['6', 1],
        'latent_image': ['6', 2], 'seed': 42, 'steps': 30, 'cfg': 3.0,
        'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0
    }},
    '8': {'class_type': 'DecodeAndSaveVideo', 'inputs': {
        'video_latent': ['7', 0], 'video_vae': ['1', 2],
        'fps': 25.0, 'filename_prefix': 'ltx2_19b_test', 'format': 'mp4', 'codec': 'h264',
        'tiling': 'disabled'
    }},
}
data = json.dumps({'prompt': prompt, 'client_id': 'ltx2test'}).encode()
req = urllib.request.Request('http://127.0.0.1:8188/prompt', data=data, headers={'Content-Type': 'application/json'})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print('Queued:', r.get('prompt_id', 'unknown'))
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f'HTTP {e.code}')
    print(body[:2000])
