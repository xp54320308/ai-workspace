from PIL import Image, ImageFilter, ImageStat
import os

test_dir = r'G:\manga_drama_project\test'
videos = ['old_params', 'rich_prompt', 'hires_720p', 'rich_motion']
frames = [0, 40, 80]

print('='*80)
print(f'{"Video":<15} {"Frame":<8} {"Sharp":<10} {"Contrast":<10} {"SizeKB":<10}')
print('='*80)

for v in videos:
    for f in frames:
        path = os.path.join(test_dir, f'{v}_f{f:03d}.png')
        if not os.path.exists(path):
            continue
        img = Image.open(path)
        edges = img.filter(ImageFilter.FIND_EDGES)
        sharp = sum(ImageStat.Stat(edges).mean) / 3
        contrast = sum(ImageStat.Stat(img).stddev) / 3
        sz = os.path.getsize(path) // 1024
        print(f'{v:<15} f{f:<6} {sharp:<10.1f} {contrast:<10.1f} {sz:<10}')
    print()
