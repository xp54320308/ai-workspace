import json, urllib.request

# Use WanImageToVideoApi - simplest approach, wraps everything
wf = {
    "1": {"class_type": "LoadImage", "inputs": {
        "image": "pipeline_keyframe.png"
    }},
    "2": {"class_type": "WanImageToVideoApi", "inputs": {
        "model": "wan2.6-i2v",
        "image": ["1", 0],
        "prompt": "smooth camera slowly panning right, gentle waves moving, seagulls flying across the sky, warm golden cinematic light",
        "negative_prompt": "blurry, distorted, ugly",
        "resolution": "480P",
        "duration": 5,
        "seed": 42
    }},
    "3": {"class_type": "SaveVideo", "inputs": {
        "video": ["2", 0],
        "filename_prefix": "pipeline_video"
    }}
}

data = json.dumps({"prompt": wf}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8188/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())
    print(f"OK: {result['prompt_id']}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Error {e.code}: {body}")
