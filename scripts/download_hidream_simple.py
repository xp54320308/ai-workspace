"""Simple direct download for remaining HiDream files."""
import os
import urllib.request

BASE = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models"
HF_BASE = "https://huggingface.co/Comfy-Org/HiDream-I1_ComfyUI/resolve/main/split_files"

FILES = [
    ("text_encoders/t5xxl_fp8_e4m3fn_scaled.safetensors", 5.16),
    ("text_encoders/llama_3.1_8b_instruct_fp8_scaled.safetensors", 9.08),
    ("diffusion_models/hidream_i1_full_fp8.safetensors", 17.1),
]

def download(rel_path, size_gb):
    target = os.path.join(BASE, rel_path)
    if os.path.exists(target):
        actual = os.path.getsize(target) / (1024**3)
        if actual > size_gb * 0.9:
            print(f"[SKIP] {rel_path} ({actual:.1f}GB)")
            return True
    
    url = f"{HF_BASE}/{rel_path}"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    print(f"[DOWNLOAD] {rel_path} ({size_gb}GB)...")
    print(f"  URL: {url}")
    
    try:
        urllib.request.urlretrieve(url, target)
        actual = os.path.getsize(target) / (1024**3)
        print(f"[DONE] {rel_path} ({actual:.1f}GB)")
        return True
    except Exception as e:
        print(f"[ERROR] {rel_path}: {e}")
        if os.path.exists(target):
            os.remove(target)
        return False

if __name__ == "__main__":
    for path, size in FILES:
        download(path, size)
