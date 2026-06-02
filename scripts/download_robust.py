"""
稳健的模型下载脚本 - 支持断点续传 + 自动重试
"""
import urllib.request
import os
import time
import ssl

URL = 'https://huggingface.co/kijai/WanVideo_comfy_fp8_scaled/resolve/main/I2V/Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
DST = r'F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models\diffusion_models\WanVideo\2_2\Wan2_2-I2V-A14B-HIGH_fp8_e4m3fn_scaled_KJ.safetensors'
tmp = DST + '.tmp'
EXPECTED = 14.0 * 1024 * 1024 * 1024  # ~14GB

os.makedirs(os.path.dirname(DST), exist_ok=True)

def download():
    # Check existing progress
    existing = os.path.getsize(tmp) if os.path.exists(tmp) else 0
    
    if existing >= EXPECTED * 0.99:
        # File is complete enough, rename
        os.rename(tmp, DST)
        print(f'File complete! Renamed to DST ({existing/1024/1024/1024:.1f}GB)', flush=True)
        return True
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    if existing > 1024 * 1024:  # Resume if > 1MB
        headers['Range'] = f'bytes={existing}-'
        print(f'Resuming from {existing/1024/1024/1024:.2f}GB', flush=True)
    else:
        print(f'Starting fresh download', flush=True)
    
    ctx = ssl.create_default_context()
    req = urllib.request.Request(URL, headers=headers)
    
    try:
        resp = urllib.request.urlopen(req, timeout=60, context=ctx)
    except Exception as e:
        print(f'Connection error: {e}', flush=True)
        return False
    
    content_length = int(resp.headers.get('Content-Length', 0))
    total = existing + content_length
    mode = 'ab' if existing > 1024 * 1024 else 'wb'
    
    print(f'Total: {total/1024/1024/1024:.1f}GB', flush=True)
    
    downloaded = existing
    start_time = time.time()
    last_report = start_time
    
    try:
        with open(tmp, mode) as f:
            while True:
                chunk = resp.read(4 * 1024 * 1024)  # 4MB
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                
                now = time.time()
                if now - last_report >= 30:  # Report every 30s
                    elapsed = now - start_time
                    speed = (downloaded - existing) / elapsed / 1024 / 1024
                    pct = downloaded / total * 100
                    remaining = total - downloaded
                    eta = remaining / (downloaded - existing) * elapsed / 60 if (downloaded - existing) > 0 else 0
                    print(f'{pct:.1f}% ({downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB) {speed:.1f}MB/s ETA:{eta:.0f}min', flush=True)
                    last_report = now
        
        # Download complete
        if downloaded >= total * 0.99:
            os.rename(tmp, DST)
            elapsed = time.time() - start_time
            print(f'DONE! {downloaded/1024/1024/1024:.1f}GB in {elapsed/60:.1f}min', flush=True)
            return True
        else:
            print(f'Incomplete: {downloaded/1024/1024/1024:.1f}/{total/1024/1024/1024:.1f}GB', flush=True)
            return False
            
    except Exception as e:
        print(f'Download error: {e}', flush=True)
        return False

# Main loop with retries
MAX_RETRIES = 20
for attempt in range(1, MAX_RETRIES + 1):
    print(f'\n--- Attempt {attempt}/{MAX_RETRIES} ---', flush=True)
    
    # Check if already done
    if os.path.exists(DST):
        sz = os.path.getsize(DST) / 1024 / 1024 / 1024
        print(f'Already done: {sz:.1f}GB', flush=True)
        break
    
    success = download()
    if success:
        break
    
    if attempt < MAX_RETRIES:
        wait = min(30, attempt * 5)
        print(f'Retrying in {wait}s...', flush=True)
        time.sleep(wait)
else:
    print(f'Failed after {MAX_RETRIES} attempts', flush=True)
