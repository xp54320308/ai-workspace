"""Download HiDream-I1 ComfyUI model files."""
import os
import sys
from huggingface_hub import hf_hub_download

REPO_ID = "Comfy-Org/HiDream-I1_ComfyUI"
BASE_DIR = r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\models"

# Files to download: (subfolder in repo split_files/, filename, target_dir)
FILES = [
    # VAE (335MB)
    ("split_files/vae", "ae.safetensors", "vae"),
    # Text Encoders
    ("split_files/text_encoders", "clip_l_hidream.safetensors", "text_encoders"),
    ("split_files/text_encoders", "clip_g_hidream.safetensors", "text_encoders"),
    ("split_files/text_encoders", "t5xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders"),
    ("split_files/text_encoders", "llama_3.1_8b_instruct_fp8_scaled.safetensors", "text_encoders"),
    # Diffusion Model (Full FP8, 17.1GB)
    ("split_files/diffusion_models", "hidream_i1_full_fp8.safetensors", "diffusion_models"),
]

def download_file(subfolder, filename, target_dir):
    """Download a single file."""
    target_path = os.path.join(BASE_DIR, target_dir, filename)
    if os.path.exists(target_path):
        print(f"[SKIP] {filename} already exists")
        return True
    
    print(f"[DOWNLOADING] {filename}...")
    try:
        path = hf_hub_download(
            repo_id=REPO_ID,
            filename=f"{subfolder}/{filename}",
            local_dir=BASE_DIR,
            local_dir_use_symlinks=False,
        )
        # Move from split_files subfolder to target_dir
        src = os.path.join(BASE_DIR, subfolder, filename)
        dst = os.path.join(BASE_DIR, target_dir, filename)
        if src != dst and os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.rename(src, dst)
            # Clean up empty split_files dirs
            try:
                os.rmdir(os.path.join(BASE_DIR, subfolder))
                parent = os.path.dirname(os.path.join(BASE_DIR, subfolder))
                if os.path.basename(parent) == "split_files" and not os.listdir(parent):
                    os.rmdir(parent)
            except OSError:
                pass
        print(f"[DONE] {filename}")
        return True
    except Exception as e:
        print(f"[ERROR] {filename}: {e}")
        return False

def main():
    task = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if task == "vae":
        files = [f for f in FILES if f[2] == "vae"]
    elif task == "text_encoders":
        files = [f for f in FILES if f[2] == "text_encoders"]
    elif task == "diffusion_models":
        files = [f for f in FILES if f[2] == "diffusion_models"]
    else:
        files = FILES
    
    success = 0
    for subfolder, filename, target_dir in files:
        if download_file(subfolder, filename, target_dir):
            success += 1
    
    print(f"\nCompleted: {success}/{len(files)} files")

if __name__ == "__main__":
    main()
