from PIL import Image, ImageFilter, ImageStat
import os

ws = os.path.expanduser(r'~\.openclaw\workspace')

print("="*70)
hdr = f"{'Version':<15} {'Frame':<8} {'Sharp':<10} {'Contrast':<10} {'KB':<8}"
print(hdr)
print("="*70)

for f in [0, 30, 60]:
    path = os.path.join(ws, f'C_jump_f{f:03d}.png')
    if os.path.exists(path):
        img = Image.open(path)
        sharp = sum(ImageStat.Stat(img.filter(ImageFilter.FIND_EDGES)).mean) / 3
        contrast = sum(ImageStat.Stat(img).stddev) / 3
        sz = os.path.getsize(path) // 1024
        print(f"{'OLD single':<15} f{f:<6} {sharp:<10.1f} {contrast:<10.1f} {sz:<8}")

print("-"*70)

for seg in ['seg1', 'seg2', 'seg3']:
    for f in [0, 40, 80]:
        path = os.path.join(ws, f'{seg}_f{f:03d}.png')
        if os.path.exists(path):
            img = Image.open(path)
            sharp = sum(ImageStat.Stat(img.filter(ImageFilter.FIND_EDGES)).mean) / 3
            contrast = sum(ImageStat.Stat(img).stddev) / 3
            sz = os.path.getsize(path) // 1024
            label = f"NEW {seg}"
            print(f"{label:<15} f{f:<6} {sharp:<10.1f} {contrast:<10.1f} {sz:<8}")
    print()
