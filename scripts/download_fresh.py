import urllib.request
import os
import time
import ssl

URL = 'https://huggingface.co/kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
DST = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
tmp = DST + '.tmp'

os.makedirs(os.path.dirname(DST), exist_ok=True)

# Try SSL context
ctx = ssl.create_default_context()

req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=60, context=ctx)
total = int(resp.headers.get('Content-Length', 0))

print(f'Total: {total/1024/1024/1024:.1f}GB', flush=True)
print(f'Downloading...', flush=True)

downloaded = 0
start_time = time.time()
last_report = start_time

with open(tmp, 'wb') as f:
    while True:
        try:
            chunk = resp.read(4 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            
            now = time.time()
            if now - last_report >= 15:
                elapsed = now - start_time
                speed = downloaded / elapsed / 1024 / 1024
                pct = downloaded / total * 100 if total else 0
                eta = (total - downloaded) / (downloaded / elapsed) / 60 if downloaded > 0 else 0
                print(f'{pct:.1f}% ({downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB) {speed:.1f}MB/s ETA:{eta:.0f}min', flush=True)
                last_report = now
        except Exception as e:
            print(f'Error during download: {e}', flush=True)
            break

if downloaded >= total:
    os.rename(tmp, DST)
    elapsed = time.time() - start_time
    print(f'DONE in {elapsed/60:.1f}min', flush=True)
else:
    print(f'Incomplete: {downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB', flush=True)
