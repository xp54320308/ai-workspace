import urllib.request
import os
import time

downloads = [
    {
        'url': 'https://huggingface.co/kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors',
        'dst': r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors',
        'size_gb': 14.0
    },
    {
        'url': 'https://huggingface.co/kijai/WanVideo_comfy_fp8_scaled/resolve/main/TI2V/Wan2_2-TI2V-5B_fp8_e4m3fn_scaled_KJ.safetensors',
        'dst': r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-TI2V-5B_fp8_e4m3fn_scaled_KJ.safetensors',
        'size_gb': 4.9
    }
]

for dl in downloads:
    dst = dl['dst']
    url = dl['url']
    name = os.path.basename(dst)
    
    # Skip if already exists
    if os.path.exists(dst):
        sz = os.path.getsize(dst) / 1024 / 1024 / 1024
        print(f'SKIP (exists): {name} ({sz:.1f}GB)', flush=True)
        continue
    
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    print(f'Downloading: {name} ({dl["size_gb"]}GB)', flush=True)
    print(f'  URL: {url}', flush=True)
    print(f'  DST: {dst}', flush=True)
    
    # Download with progress
    tmp = dst + '.tmp'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        total = int(resp.headers.get('Content-Length', 0))
        
        downloaded = 0
        start_time = time.time()
        last_report = start_time
        
        with open(tmp, 'wb') as f:
            while True:
                chunk = resp.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                now = time.time()
                if now - last_report >= 10:  # Report every 10s
                    elapsed = now - start_time
                    speed = downloaded / elapsed / 1024 / 1024
                    pct = downloaded / total * 100 if total else 0
                    print(f'  {pct:.1f}% ({downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB) {speed:.1f}MB/s', flush=True)
                    last_report = now
        
        # Rename tmp to final
        os.rename(tmp, dst)
        elapsed = time.time() - start_time
        print(f'  DONE: {name} in {elapsed:.0f}s ({elapsed/60:.1f}min)', flush=True)
        
    except Exception as e:
        print(f'  ERROR: {e}', flush=True)
        if os.path.exists(tmp):
            os.remove(tmp)

print('\nAll downloads complete!', flush=True)
