from PIL import Image, ImageFilter, ImageStat
import os

ws = os.path.expanduser(r'~\.openclaw\workspace')
old_dir = r'G:\manga_drama_project\test'

pairs = [
    ('old_params', 'v7', 'Frame 0', 0),
    ('old_params', 'v7', 'Frame 20', 20),
    ('old_params', 'v7', 'Frame 40', 40),
    ('old_params', 'v7', 'Frame 60', 60),
    ('old_params', 'v7', 'Frame 80', 80),
]

print(f'{"Frame":<10} {"Old Sharp":<12} {"New Sharp":<12} {"Diff":<10} {"Old KB":<10} {"New KB":<10}')
print('='*70)

for old_prefix, new_prefix, label, f in pairs:
    old_path = os.path.join(old_dir, f'{old_prefix}_f{f:03d}.png')
    new_path = os.path.join(ws, f'{new_prefix}_f{f:03d}.png')
    if not os.path.exists(old_path) or not os.path.exists(new_path):
        continue
    old_img = Image.open(old_path)
    new_img = Image.open(new_path)
    old_sharp = sum(ImageStat.Stat(old_img.filter(ImageFilter.FIND_EDGES)).mean) / 3
    new_sharp = sum(ImageStat.Stat(new_img.filter(ImageFilter.FIND_EDGES)).mean) / 3
    old_kb = os.path.getsize(old_path) // 1024
    new_kb = os.path.getsize(new_path) // 1024
    diff_pct = (new_sharp / old_sharp - 1) * 100 if old_sharp > 0 else 0
    print(f'{label:<10} {old_sharp:<12.1f} {new_sharp:<12.1f} {diff_pct:+.0f}%      {old_kb:<10} {new_kb:<10}')
