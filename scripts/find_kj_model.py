import urllib.request, json

# Check the fp8_scaled repo subdirectories
for subdir in ['I2V', 'TI2V']:
    url = f'https://huggingface.co/api/models/kijai/WanVideo_comfy_fp8_scaled/tree/main/{subdir}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        print(f'=== {subdir} ===')
        for item in data:
            name = item.get('path', '')
            sz = item.get('size', 0) / 1024 / 1024 / 1024
            print(f'  {name}: {sz:.1f}GB')
        print()
    except Exception as e:
        print(f'{subdir}: {e}')
