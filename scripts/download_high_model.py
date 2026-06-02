import urllib.request
import os
import time
import threading

# Try Chinese HuggingFace mirror first
MIRRORS = [
    'https://hf-mirror.com',
    'https://huggingface.co',
]

REPO = 'kijai/WanVideo_comfy_fp8_scaled'
FILE = 'I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
DST = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'

os.makedirs(os.path.dirname(DST), exist_ok=True)

# Test mirrors
print('Testing mirrors...', flush=True)
working_mirror = None
for mirror in MIRRORS:
    url = f'{mirror}/{REPO}/resolve/main/{FILE}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
        resp = urllib.request.urlopen(req, timeout=10)
        total = int(resp.headers.get('Content-Length', 0))
        print(f'  {mirror}: OK ({total/1024/1024/1024:.1f}GB)', flush=True)
        working_mirror = mirror
        break
    except Exception as e:
        print(f'  {mirror}: FAIL ({e})', flush=True)

if not working_mirror:
    print('No working mirror found!', flush=True)
    exit(1)

url = f'{working_mirror}/{REPO}/resolve/main/{FILE}'
tmp = DST + '.tmp'

print(f'\nDownloading from: {working_mirror}', flush=True)
print(f'File: {FILE}', flush=True)

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    total = int(resp.headers.get('Content-Length', 0))
    
    downloaded = 0
    start_time = time.time()
    last_report = start_time
    
    with open(tmp, 'wb') as f:
        while True:
            chunk = resp.read(4 * 1024 * 1024)  # 4MB chunks for faster download
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            
            now = time.time()
            if now - last_report >= 5:  # Report every 5s
                elapsed = now - start_time
                speed = downloaded / elapsed / 1024 / 1024
                pct = downloaded / total * 100 if total else 0
                eta = (total - downloaded) / (downloaded / elapsed) / 60 if downloaded > 0 else 0
                print(f'  {pct:.1f}% ({downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB) {speed:.1f}MB/s ETA:{eta:.0f}min', flush=True)
                last_report = now
    
    os.rename(tmp, DST)
    elapsed = time.time() - start_time
    print(f'\nDONE in {elapsed/60:.1f}min ({elapsed:.0f}s)', flush=True)
    print(f'Saved: {DST}', flush=True)
    
except Exception as e:
    print(f'ERROR: {e}', flush=True)
    if os.path.exists(tmp):
        os.remove(tmp)
