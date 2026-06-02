#!/usr/bin/env python3
"""Generate first/last frame images for all 3 shots using Qwen Image Edit."""
import json, urllib.request, time, copy

API = "http://127.0.0.1:8188"
WORKFLOW = r"F:\Comfyui\ComfyUI-aki-v3\user\default\workflows\I2V首尾帧.json"

with open(WORKFLOW, 'r', encoding='utf-8-sig') as f:
    base_wf = json.load(f)

shots = {
    "shot_01": {
        "first_edit": "改为：短发少年穿白色校服衬衫蓝领带，站在学校大门前，午后阳光，樱花飘落，动漫风格，9:16竖屏",
        "last_edit": "改为：短发少年穿白色校服衬衫蓝领带，伸手接住飘落的樱花花瓣，学校大门背景，动漫风格，9:16竖屏",
    },
    "shot_02": {
        "first_edit": "改为：长发少女穿粉色连衣裙白色蝴蝶结，站在学校天台栏杆旁，蓝天白云，风吹动长发，动漫风格，9:16竖屏",
        "last_edit": "改为：长发少女穿粉色连衣裙白色蝴蝶结，在学校天台转身微笑，风吹动长发，动漫风格，9:16竖屏",
    },
    "shot_03": {
        "first_edit": "改为：短发少年和长发少女在学校樱花树下相遇，午后阳光，樱花飘落，动漫风格，9:16竖屏",
        "last_edit": "改为：短发少年和长发少女面对面站在樱花树下，花瓣飘落，金色光线，动漫风格，9:16竖屏",
    },
}

def submit_edit(image_name, edit_prompt, output_name):
    wf = copy.deepcopy(base_wf)
    for nid, node in wf.items():
        if node.get("class_type") == "LoadImage":
            node["inputs"]["image"] = image_name
        elif node.get("class_type") == "QwenImageEdit":
            node["inputs"]["prompt"] = edit_prompt
        elif node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = output_name
    payload = {"prompt": wf}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{API}/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return result.get("prompt_id")

tasks = []
for shot_id, shot in shots.items():
    pid = submit_edit("首帧.png", shot["first_edit"], f"{shot_id}_first")
    tasks.append({"shot": shot_id, "frame": "first", "pid": pid})
    print(f"[提交] {shot_id} first -> {pid[:12]}...")
    time.sleep(1)
    pid = submit_edit("尾帧.png", shot["last_edit"], f"{shot_id}_last")
    tasks.append({"shot": shot_id, "frame": "last", "pid": pid})
    print(f"[提交] {shot_id} last -> {pid[:12]}...")
    time.sleep(1)

with open(r"G:\manga_drama_project\scripts\pending_tasks.json", "w") as f:
    json.dump(tasks, f, indent=2)
print(f"\n已提交 {len(tasks)} 个图片生成任务")
