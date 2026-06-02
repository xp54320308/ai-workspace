---
name: comfyui-comic-drama-pipeline
description: |
  Build AI comic/drama (漫剧) video generation pipelines in ComfyUI.
  Covers character consistency, multi-scene keyframe generation with Qwen Image Edit,
  Wan2.2 I2V video generation, and batch concatenation. Optimized for RTX 5090 (23GB).
---

# AI 漫剧制作 Pipeline (ComfyUI)

## When to Use
Generating multi-scene animated comic/drama videos with consistent characters across scenes.

## Core Concept: Two-Phase Architecture

DON'T try to generate everything at once. Qwen Image Edit (19GB) + Wan2.2 (13GB) can't coexist in 23GB VRAM.

```
Phase 1: Qwen Image Edit → Generate 4 keyframes (save to disk)
    ↓ PURGE VRAM ↓
Phase 2: Wan2.2 I2V → Load keyframes from disk → Generate video clips
```

## Workflow Architecture

```
┌─────────────── Phase 1: Keyframe Generation ───────────────┐
│                                                              │
│  角色定装照 ─→ Qwen UNET ─→ LoRA多角度 ─→ LoRA加速          │
│       │            │                                        │
│  Qwen CLIP ─→ TextEncodeQwenImageEditPlus (指令)            │
│       │                  │                                   │
│  EmptyLatent ─────────→ KSampler(4步) → VAEDecode → Save    │
│                                                              │
│  ×4 次 (Shot1首帧, Shot1尾帧, Shot2首帧, Shot2尾帧)         │
└──────────────────────────────────────────────────────────────┘
                              ↓
                     ⚠️ 手动切换阶段
                              ↓
┌─────────────── Phase 2: Video Generation ──────────────────┐
│                                                              │
│  LoadImage(从Phase1输出选图) → CLIPVisionEncode ─┐          │
│  LoadImage(从Phase1输出选图) → CLIPVisionEncode ─┤          │
│  Wan CLIP → CLIPTextEncode(+/-) ────────────────→│          │
│                                                    │          │
│  Wan UNET_H → LoRA → BlockSwap → KSampler1 ─→ KSampler2    │
│  Wan UNET_L → LoRA → BlockSwap ─────────────────┘    │      │
│                                                  VAEDecode   │
│                                                     │        │
│                                        ImageResizeKJv2→720p │
│                                                     │        │
│                                               VHS_VideoCombine│
│                                                              │
│  ×2 次 (Shot1, Shot2)                                        │
└──────────────────────────────────────────────────────────────┘
```

## Models Required

### Qwen Image Edit (Phase 1)
| Model | Location | Size |
|-------|----------|------|
| qwen_image_edit_2509_fp8_e4m3fn.safetensors | diffusion_models/ | 19GB |
| qwen_2.5_vl_7b_fp8_scaled.safetensors | text_encoders/ | 8.7GB |
| qwen_image_vae.safetensors | vae/ | 0.2GB |
| Qwen-Edit-2509-Multiple-angles.safetensors | loras/ | 0.2GB |
| Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors | loras/ | 0.8GB |

### Wan2.2 I2V (Phase 2)
Same as comfyui-wan2.2-firstlastframe skill.

## Character Consistency Rules

| Technique | How | Quality |
|-----------|-----|---------|
| **Same reference image** | All TextEncodeQwenImageEditPlus use same LoadImage | ⭐⭐⭐⭐⭐ |
| **LoRA 多角度** | `Qwen-Edit-2509-Multiple-angles` at strength 0.8 | ⭐⭐⭐⭐ |
| **Fixed character description** | CLIPTextEncode with character details, shared across shots | ⭐⭐⭐ |
| **Only change action** | Each shot's instruction changes pose/action, not character | Required |

## Keyframe Selection Rules (CRITICAL)

Bad keyframes = bad video. Follow these rules:

```
✅ Same background, lighting, angle across frames in same shot
✅ Only change character's pose/action/expression
✅ Change ≤ 30% between first and last frame of same shot

❌ Different backgrounds between first/last frame
❌ Different camera angles
❌ Different lighting direction
❌ Character appearance changes
```

Between DIFFERENT shots, you CAN change everything (hard cut).

## Shot Planning Template

For a 2-shot, 10-second drama:

```
Shot 1 (5 sec, 81 frames):
  首帧: 猫安静坐在窗边看窗外
  尾帧: 猫站起来伸懒腰 (同背景同光线)
  → Wan2.2 generates smooth motion between

Shot 2 (5 sec, 81 frames):
  首帧: 猫转身看向房间 (新场景 OK)
  尾帧: 猫跳下窗台走向房间深处 (同 Shot2 背景)
  → Wan2.2 generates smooth motion between

Final: ffmpeg concat Shot1.mp4 Shot2.mp4 → 10-second drama
```

## VRAM Budget (RTX 5090, 23GB)

| Phase | Peak VRAM | Models Loaded |
|-------|-----------|---------------|
| Phase 1 (Qwen) | ~22GB | qwen_unet + qwen_clip + qwen_vae + 2 LoRA |
| Phase 2 (Wan) | ~21GB | wan_unet + wan_clip + wan_vae + clip_vision + 2 LoRA |

Cannot run both phases simultaneously. Always purge between phases.

## TextEncodeQwenImageEditPlus Prompts

Character description (shared, don't change):
```
A cute fluffy orange tabby cat with white chest, green eyes
```

Shot instruction (changes per shot):
```
# Shot1 首帧
The cat is sitting calmly on a windowsill, looking out the window peacefully, warm golden lighting

# Shot1 尾帧
The cat stands up on the windowsill, stretching its front paws forward curiously, same background, same lighting
```

Always include "same background, same lighting" in the instruction to maintain scene consistency.

## FFmpeg Concatenation

```bash
# Simple concat (same resolution/framerate)
ffmpeg -i Shot1.mp4 -i Shot2.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0" \
  output_漫剧.mp4

# With crossfade transition (2 second dissolve)
ffmpeg -i Shot1.mp4 -i Shot2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=2:offset=4" \
  output_漫剧.mp4
```

## Civitai Wan2.2 工作流调研（2026-04-26）

关键参考工作流（Civitai API: `curl "https://civitai.com/api/v1/models?types[]=Workflows&query=wan2.2"`）：

### ⭐ SVI FFLF Workflow（下载 274）— 漫剧最相关
`https://civitai.com/models/2534583`
BaseModel: Wan Video 2.2 I2V-A14B
- **核心功能**：分段式首帧-尾帧（FFLF）视频生成，自定义节点保存 latent 文件，随时加载继续生成
- **关键**：需要额外下载 **SVI v2 PRO LoRA**（本地没有）：
  - `SVI_v2_PRO_Wan2.2-I2V-A14B_HIGH_lora_rank_128_fp16.safetensors`
  - `SVI_v2_PRO_Wan2.2-I2V-A14B_LOW_lora_rank_128_fp16.safetensors`
  - 下载：`https://huggingface.co/Kijai/WanVideo_comfy/tree/main/LoRAs/Stable-Video-Infinity/v2.0`
- **对漫剧的价值**：分段生成 → 拼接，正是长视频制作核心

### WAN2.2 14B AIO Basic（下载 148）
`https://civitai.com/models/2530365`
BaseModel: Wan Video 14B i2v 720p
- 整合 Sage Attention + NAG + FLV 全部优化技巧

### TFM Pocket RPG Style（下载 64）
`https://civitai.com/models/2548223`
BaseModel: Wan Video 2.2 T2V-A14B
- 动漫/游戏 Pocket RPG 风格 LoRA，可参考训练思路

## 本地模型最佳漫剧搭配（5秒）

```
关键帧生成
└── qwen_image_edit_2509_fp8 + Qwen-Edit-2509-Multiple-angles LoRA
    （你的桌面工作流已是这套）

视频生成（方案A — 首尾帧I2V）
└── wan2.2_i2v_high_noise_14B_fp8_scaled + wan2.2_i2v_low_noise_14B_fp8_scaled
    + wan2.2_i2v_lightx2v_4steps_lora（高/低噪声）
    → 需要首帧+尾帧，适合相邻镜头衔接

视频生成（方案B — 单图TI2V，备选）
└── wan2.2_ti2v_5B_fp16（720p@24fps，4090单卡可跑）
    → 只需一张图+文字，比I2V 14B门槛低，分辨率更高
    → 本地有此模型但工作流未使用

⚠️ 缺失：SVI v2 PRO LoRA（High/Low）需从 HuggingFace 下载才能用 SVI FFLF 工作流
```

## 已知坑（2026-04-26 实测）

| 坑 | 状态 |
|-----|------|
| hunyuanvideo1.5_1080p_sr_distilled_fp16 .safetensors（尾空格） | ✅ 已修复 |
| ltx-2.3-22b-distilled-fp8 .safetensors（尾空格） | ✅ 已修复 |
| SVI v2 PRO LoRA 缺失 | ⚠️ 需手动下载 |
| lightx2v 4-step 导致慢动作 | 用 PainterLongVideo 的 motion_amplitude 修复 |

| Problem | Cause | Fix |
|---------|-------|-----|
| Character looks different between shots | Different reference image or prompt | Use exact same reference + description |
| Video is blurry/distorted | First/last frames too different | Reduce difference, same background |
| Video is static/frozen | Frames too similar or anti-static missing | Add "dynamic motion" to positive prompt |
| OOM in Phase 1 | Too many models loaded | Confirm Phase 1 only loads Qwen models |
| OOM in Phase 2 | BlockSwap not working | Verify wanBlockSwap nodes connected |

## Per-Shot Transition Prompt (关键!)

每个 Shot 需要独立的 transition_prompt 描述首帧→尾帧之间的具体动作。

WanFirstLastFrameToVideo 的 positive 提示词必须是**动作过渡描述**, 不是画面描述:

```python
# WRONG: too generic
"smooth animation, detailed, cinematic motion, high quality"

# CORRECT: describes specific transition
"The cat gradually stands up from sitting position, stretching its front paws forward, 
 body extending smoothly, maintaining the same warm lighting and wooden windowsill background"
```

三要素缺一不可:
1. CLIPVision(首帧) → 模型知道起点
2. CLIPVision(尾帧) → 模型知道终点
3. transition_prompt → 模型知道怎么走过去

脚本中的 DEFAULT_SCRIPT 应包含 transition_prompt 字段:
```python
{
    "name": "Shot1",
    "start_prompt": "...",  # Qwen编辑用: 生成首帧图片
    "end_prompt": "...",    # Qwen编辑用: 生成尾帧图片
    "transition_prompt": "...",  # Wan用: 描述首帧→尾帧的动作
}
```

## Slow Motion Fix (4-step LoRA)

lightx2v 4-step LoRA 会导致视频慢动作。使用 PainterLongVideo 节点的 motion_amplitude:
- 1.0 = 正常, 1.15 = 推荐修复, 2.0 = 最大加速

插件: `git clone https://github.com/princepainter/ComfyUI-PainterNodes.git`

## Qwen Image Edit Bug Fixes

内置 TextEncodeQwenImageEditPlus 有两个坑:
1. **pixel offset**: 强制缩放导致偏移 → 用 `comfyui_qwen_image_edit_adv` 替代
2. **参数名**: 图片参数是 `image1` 不是 `image`

推荐参数: Resolution=1024, Alignment=32, CFG=1.0-2.5

## Essential Plugins (完整清单)

```bash
cd F:\Comfyui\ComfyUI-aki-v3\ComfyUI\custom_nodes

# 26节点全家桶 (LongVideo+音频驱动+Qwen编辑+VRAM管理)
git clone https://github.com/princepainter/ComfyUI-PainterNodes.git

# Qwen偏移修复+多图编辑 (10图+遮罩+零偏移)
git clone https://github.com/lenML/comfyui_qwen_image_edit_adv.git

# AI视频拼接 (VACE生成过渡帧)
git clone https://github.com/stuttlepress/ComfyUI-Wan-VACE-Video-Joiner.git

# 3D机位选择 (96种角度)
git clone https://github.com/NickPittas/ComfyUI_CameraAngleSelector.git

# LLM集成 (Ollama/Claude/GPT/DeepSeek)
git clone https://github.com/heshengtao/comfyui_LLM_party.git

# 提示词自动改写
git clone https://github.com/lihaoyun6/ComfyUI-QwenPromptRewriter.git
```

## ComfyUI API Automation (Python)

```python
import urllib.request, json, time

COMFYUI_URL = "http://127.0.0.1:8188"

def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{COMFYUI_URL}/prompt", data=data,
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

def wait_for_completion(prompt_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        history = json.loads(urllib.request.urlopen(
            f"{COMFYUI_URL}/history/{prompt_id}").read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)

def upload_image(local_path):
    import mimetypes
    filename = os.path.basename(local_path)
    boundary = "----FormBoundary"
    with open(local_path, "rb") as f:
        file_data = f.read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
            f'filename="{filename}"\r\n\r\n').encode() + file_data + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(f"{COMFYUI_URL}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(urllib.request.urlopen(req).read()).get("name", filename)
```

Workflow JSON uses node IDs as string keys: `{"1": {"class_type": "...", "inputs": {...}}}`
Links reference other nodes: `["node_id", output_slot_index]`
