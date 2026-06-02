import importlib
import sys

deps = [
    "torch", "torchvision", "numpy", "PIL", "imageio",
    "pyrallis", "diffusers", "transformers", "xformers",
    "flash_attn", "triton", "safetensors", "einops",
    "timm", "sentencepiece", "huggingface_hub"
]

print(f"Python: {sys.version}")
print()

for dep in deps:
    try:
        mod = importlib.import_module(dep)
        ver = getattr(mod, "__version__", "installed")
        print(f"  OK  {dep}: {ver}")
    except ImportError:
        print(f"  MISSING  {dep}")
    except Exception as e:
        print(f"  ERROR  {dep}: {e}")

# Check CUDA
try:
    import torch
    print(f"\nCUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1024**3:.1f} GB")
except:
    pass
