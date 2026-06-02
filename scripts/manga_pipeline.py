#!/usr/bin/env python3
"""漫剧工厂 Pipeline - 单镜头测试"""
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import uuid
import subprocess
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
PROJECT_DIR = Path(r"G:\manga_drama_project")
WORKFLOW_TEMPLATE = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\user\default\workflows\AKI_first_last_I2V_big_action_v57_API.json")
FFMPEG = r"F:\Comfyui\ComfyUI-aki-v3\python\ffmpeg.exe"
COMFYUI_INPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\input")
COMFYUI_OUTPUT = Path(r"F:\Comfyui\ComfyUI-aki-v3\ComfyUI\output")

# ========== 质量参数（关键！） ===========
QUALITY = {
    "steps": 30,            # 总步数（原22，提升到30）
    "cfg": 5.5,             # CFG引导强度（原4.0，提升到5.5）
    "sampler": "dpmpp_2m_sde",  # 采样器（原euler，换更强的）
    "scheduler": "karras",       # 调度器（原simple，换karras）
    "shift": 8.0,           # ModelSamplingSD3 shift（5-12可调）
}
SPLIT_RATIO = 0.5  # HIGH/LOW 模型各占多少步（0.5 = 各一半）

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def queue_prompt(prompt):
    client_id = str(uuid.uuid4())
    body = json.dumps({"prompt": prompt, "client_id": client_id}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["prompt_id"]

def wait_for_result(prompt_id, timeout=1800):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{COMFYUI_URL}/history/{urllib.parse.quote(prompt_id)}", timeout=30) as resp:
                history = json.loads(resp.read())
                if prompt_id in history:
                    return history[prompt_id]
        except:
            pass
        time.sleep(3)
    raise TimeoutError(f"Timeout waiting for {prompt_id}")

def generate_shot(shot, episode_name):
    """为一个镜头生成首尾帧图片和视频"""
    shot_id = shot["id"]
    print(f"\n=== 处理镜头 {shot_id} ===")
    
    # 1. 生成首帧图片（使用 ComfyUI text-to-image 或直接用已有图片）
    first_img_name = f"{episode_name}_{shot_id}_first.png"
    last_img_name = f"{episode_name}_{shot_id}_last.png"
    
    # 检查首尾帧图片是否已存在于 input 目录
    first_img_path = COMFYUI_INPUT / first_img_name
    last_img_path = COMFYUI_INPUT / last_img_name
    
    if not first_img_path.exists() or not last_img_path.exists():
        print(f"  ⚠️ 首尾帧图片不存在，需要先生成:")
        print(f"    首帧: {first_img_path}")
        print(f"    尾帧: {last_img_path}")
        print(f"  请先用 ComfyUI 生成这两张图片，或用 Qwen Image Edit 生成")
        return None
    
    # 2. 加载工作流模板
    wf = load_json(WORKFLOW_TEMPLATE)
    
    # 3. 修改工作流参数
    # 节点 7: positive prompt
    wf["7"]["inputs"]["text"] = shot["motion_prompt"]
    # 节点 9: first frame image
    wf["9"]["inputs"]["image"] = first_img_name
    # 节点 10: last frame image
    wf["10"]["inputs"]["image"] = last_img_name
    # 节点 11: video dimensions (9:16 vertical)
    wf["11"]["inputs"]["width"] = 480
    wf["11"]["inputs"]["height"] = 832
    wf["11"]["inputs"]["length"] = 81  # ~5 seconds at 16fps
    # 节点 16: output filename
    wf["16"]["inputs"]["filename_prefix"] = f"{episode_name}/{shot_id}"

    # ========== 质量覆盖（核心修复） ===========
    split_step = int(QUALITY["steps"] * SPLIT_RATIO)

    # Node 5/6: ModelSamplingSD3 shift
    if "5" in wf and "inputs" in wf["5"]:
        wf["5"]["inputs"]["shift"] = QUALITY["shift"]
    if "6" in wf and "inputs" in wf["6"]:
        wf["6"]["inputs"]["shift"] = QUALITY["shift"]

    # Node 12: HIGH noise sampler (前半段)
    if "12" in wf:
        wf["12"]["inputs"]["steps"] = QUALITY["steps"]
        wf["12"]["inputs"]["cfg"] = QUALITY["cfg"]
        wf["12"]["inputs"]["sampler_name"] = QUALITY["sampler"]
        wf["12"]["inputs"]["scheduler"] = QUALITY["scheduler"]
        wf["12"]["inputs"]["end_at_step"] = split_step

    # Node 13: LOW noise sampler (后半段)
    if "13" in wf:
        wf["13"]["inputs"]["steps"] = QUALITY["steps"]
        wf["13"]["inputs"]["cfg"] = QUALITY["cfg"]
        wf["13"]["inputs"]["sampler_name"] = QUALITY["sampler"]
        wf["13"]["inputs"]["scheduler"] = QUALITY["scheduler"]
        wf["13"]["inputs"]["start_at_step"] = split_step

    print(f"  质量参数: steps={QUALITY['steps']}({split_step}+{QUALITY['steps']-split_step}), "
          f"cfg={QUALITY['cfg']}, sampler={QUALITY['sampler']}, shift={QUALITY['shift']}")

    # 4. 提交到 ComfyUI
    print(f"  提交视频生成任务...")
    prompt_id = queue_prompt(wf)
    print(f"  Prompt ID: {prompt_id}")
    
    # 5. 等待结果
    print(f"  等待生成完成（最长30分钟）...")
    result = wait_for_result(prompt_id)
    
    # 6. 检查输出
    outputs = result.get("outputs", {})
    for node_id, node_output in outputs.items():
        if "videos" in node_output:
            for video in node_output["videos"]:
                src = Path(video["filename"])
                print(f"  ✅ 视频生成完成: {src}")
                return str(COMFYUI_OUTPUT / src)
    
    print(f"  ❌ 未找到输出视频")
    return None

def main():
    # 加载剧本
    episode = load_json(PROJECT_DIR / "scripts" / "episode_01.json")
    episode_name = episode["project"]
    
    print(f"开始生成漫剧: {episode_name}")
    print(f"镜头数: {len(episode['shots'])}")
    
    # 检查 ComfyUI 是否可用
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=5) as resp:
            stats = json.loads(resp.read())
            print(f"ComfyUI 版本: {stats['system']['comfyui_version']}")
            vram = stats['devices'][0]['vram_free'] / 1e9
            print(f"GPU VRAM 可用: {vram:.1f}GB")
    except Exception as e:
        print(f"❌ ComfyUI 不可用: {e}")
        sys.exit(1)
    
    # 处理每个镜头
    results = []
    for shot in episode["shots"]:
        video_path = generate_shot(shot, episode_name)
        results.append({
            "shot_id": shot["id"],
            "video_path": video_path,
            "status": "done" if video_path else "needs_first_last_frames"
        })
    
    # 保存结果
    save_json(PROJECT_DIR / "logs" / "run_results.json", results)
    
    # 汇总
    done = sum(1 for r in results if r["status"] == "done")
    print(f"\n=== 完成: {done}/{len(results)} 镜头已生成 ===")
    for r in results:
        status = "✅" if r["status"] == "done" else "⏳"
        print(f"  {status} {r['shot_id']}: {r['status']}")

if __name__ == "__main__":
    main()
