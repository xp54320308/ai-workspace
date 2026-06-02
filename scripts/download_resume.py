import urllib.request
import os
import time

URL = 'https://huggingface.co/kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
DST = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
tmp = DST + '.tmp'

# Check existing partial download
existing = 0
if os.path.exists(tmp):
    existing = os.path.getsize(tmp)
    print(f'Resuming from {existing/1024/1024/1024:.2f}GB', flush=True)

headers = {'User-Agent': 'Mozilla/5.0'}
if existing > 0:
    headers['Range'] = f'bytes={existing}-'

req = urllib.request.Request(URL, headers=headers)
resp = urllib.request.urlopen(req, timeout=30)
total = int(resp.headers.get('Content-Length', 0)) + existing
mode = 'ab' if existing > 0 else 'wb'

print(f'Total: {total/1024/1024/1024:.1f}GB', flush=True)
print(f'Downloading...', flush=True)

downloaded = existing
start_time = time.time()
last_report = start_time

with open(tmp, mode) as f:
    while True:
        chunk = resp.read(4 * 1024 * 1024)  # 4MB
        if not chunk:
            break
        f.write(chunk)
        downloaded += len(chunk)
        
        now = time.time()
        if now - last_report >= 10:
            elapsed = now - start_time
            speed = (downloaded - existing) / elapsed / 1024 / 1024 if elapsed > 0 else 0
            pct = downloaded / total * 100
            eta = (total - downloaded) / ((downloaded - existing) / elapsed) / 60 if (downloaded - existing) > 0 else 0
            print(f'{pct:.1f}% ({downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB) {speed:.1f}MB/s ETA:{eta:.0f}min', flush=True)
            last_report = now

os.rename(tmp, DST)
elapsed = time.time() - start_time
print(f'DONE in {elapsed/60:.1f}min', flush=True)
print(f'Saved: {DST}', flush=True)
