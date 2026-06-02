import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from huggingface_hub import hf_hub_download
import time

REPO = 'kijai/WanVideo_comfy_fp8_scaled'
FILE = 'I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
DST_DIR = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2'

print(f'Downloading {FILE}...', flush=True)
print(f'Mirror: {os.environ["HF_ENDPOINT"]}', flush=True)

start = time.time()
try:
    path = hf_hub_download(
        repo_id=REPO,
        filename=FILE,
        local_dir=DST_DIR,
        resume_download=True,
    )
    elapsed = time.time() - start
    sz = os.path.getsize(path) / 1024 / 1024 / 1024
    print(f'DONE: {path} ({sz:.1f}GB) in {elapsed/60:.1f}min', flush=True)
except Exception as e:
    print(f'Error with mirror: {e}', flush=True)
    print('Trying direct HuggingFace...', flush=True)
    os.environ.pop('HF_ENDPOINT', None)
    try:
        path = hf_hub_download(
            repo_id=REPO,
            filename=FILE,
            local_dir=DST_DIR,
            resume_download=True,
        )
        elapsed = time.time() - start
        sz = os.path.getsize(path) / 1024 / 1024 / 1024
        print(f'DONE: {path} ({sz:.1f}GB) in {elapsed/60:.1f}min', flush=True)
    except Exception as e2:
        print(f'Error: {e2}', flush=True)
