import json, urllib.request

COMFYUI = 'http://127.0.0.1:8188'

nodes = {}
nodes['1'] = {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sd_xl_base_1.0.safetensors'}}
nodes['7'] = {'class_type': 'CLIPVisionLoader', 'inputs': {'clip_name': 'ipadapter_sd15_model.safetensors'}}
nodes['10'] = {'class_type': 'IPAdapterModelLoader', 'inputs': {'ipadapter_file': 'ip-adapter-plus_sdxl_vit-h.safetensors'}}
nodes['3'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'test negative', 'clip': ['1', 1]}}
nodes['img_0'] = {'class_type': 'LoadImage', 'inputs': {'image': 'portrait_A.png'}}
nodes['mask_0'] = {'class_type': 'MaskRectArea', 'inputs': {'x': 0, 'y': 0, 'width': 512, 'height': 1024, 'blur_radius': 5}}
nodes['pos_0'] = {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'black hair blue eyes white dress', 'clip': ['1', 1]}}
nodes['ip_0'] = {'class_type': 'IPAdapterAdvanced', 'inputs': {
    'model': ['1', 0], 'ipadapter': ['10', 0], 'image': ['img_0', 0],
    'weight': 1.2, 'weight_type': 'ease out', 'combine_embeds': 'concat',
    'start_at': 0.0, 'end_at': 1.0, 'embeds_scaling': 'K+V w/ C penalty',
    'attn_mask': ['mask_0', 0], 'clip_vision': ['7', 0]
}}
nodes['latent'] = {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}}
nodes['sampler'] = {'class_type': 'KSampler', 'inputs': {
    'model': ['ip_0', 0], 'positive': ['pos_0', 0], 'negative': ['3', 0],
    'latent_image': ['latent', 0], 'seed': 42, 'steps': 15, 'cfg': 7.0,
    'sampler_name': 'dpmpp_2m_sde', 'scheduler': 'karras', 'denoise': 1.0
}}
nodes['decode'] = {'class_type': 'VAEDecode', 'inputs': {'samples': ['sampler', 0], 'vae': ['1', 2]}}
nodes['save'] = {'class_type': 'SaveImage', 'inputs': {'images': ['decode', 0], 'filename_prefix': 'test_ipa'}}

data = json.dumps({'prompt': nodes, 'client_id': 'test_ipa'}).encode()
req = urllib.request.Request(COMFYUI + '/prompt', data=data, headers={'Content-Type': 'application/json'})
try:
    r = json.loads(urllib.request.urlopen(req).read())
    print('Queued: ' + r['prompt_id'])
except urllib.error.HTTPError as e:
    print('HTTP %d: %s' % (e.code, e.read().decode()))
except Exception as e:
    print('Error: %s' % e)
