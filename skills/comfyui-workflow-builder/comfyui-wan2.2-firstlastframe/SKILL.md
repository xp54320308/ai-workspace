---
name: comfyui-wan2.2-firstlastframe
description: Build Wan2.2 I2V first-last frame video workflows in ComfyUI, optimized for consumer GPUs with BlockSwap. Covers JSON format requirements, VRAM estimation, and resolution planning.
---

# Wan2.2 I2V First-Last Frame Workflow Builder

## When to Use
Building ComfyUI workflows for image-to-video generation with first/last frame control using Wan2.2 models, especially on VRAM-constrained GPUs (24GB or less).

## Core Architecture

```
首帧.png -> CLIPVisionEncode ---+
                                +-> WanFirstLastFrameToVideo -> Latent
尾帧.png -> CLIPVisionEncode ---+       |
UNET_H -> LoRA_H -> BlockSwap -> Stage1 (High Noise)
UNET_L -> LoRA_L -> BlockSwap -> Stage2 (Low Noise)
                                  |
                             VAEDecode -> MP4
```

## Required Models

| Model | Location | Size | Purpose |
|-------|----------|------|---------|
| wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors | diffusion_models/ | 13.3GB | Stage 1 |
| wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors | diffusion_models/ | 13.3GB | Stage 2 |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | text_encoders/ | 6.3GB | Text encoder |
| wan_2.1_vae.safetensors | vae/ | 0.2GB | VAE decoder |
| clip_vision_h.safetensors | clip_vision/ | 1.2GB | CLIP vision |
| wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors | loras/ | 1.1GB | Fast LoRA (high) |
| wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors | loras/ | 1.1GB | Fast LoRA (low) |

NOTE: Wan2.2 models live in diffusion_models/, NOT unet/. If UNETLoader cant find them, copy/link to unet/.

## CRITICAL: ComfyUI JSON Format Gotchas

### 1. WanFirstLastFrameToVideo Output Slots (TOP ERROR SOURCE)

slot 0: positive (CONDITIONING) -- NOT latent!
slot 1: negative (CONDITIONING)
slot 2: latent (LATENT) -- THIS is what KSampler needs

Connect KSampler latent_image to slot 2, NOT slot 0:

```python
# CORRECT
L(wan_node, 2, ksampler, 3, "LATENT")
# WRONG -- gives "received_type(CONDITIONING) mismatch input_type(LATENT)"
L(wan_node, 0, ksampler, 3, "LATENT")
```

### 2. VHS_VideoCombine widgets_values is a DICT not a LIST

Using a list causes format: False not in list and loop_count: None errors.

```python
# CORRECT -- dict with named keys
"widgets_values": {
    "save_output": True,
    "filename_prefix": "output_name",
    "loop_count": 0,
    "pix_fmt": "yuv420p",
    "save_metadata": False,
    "crf": 15,
    "trim_to_audio": False,
    "format": "video/h264-mp4",
    "no_preview": False,
    "frame_rate": 16,
    "pingpong": False
}
# WRONG -- list format
"widgets_values": [16, "video/h264-mp4", 20, False, True]
```

### 3. CLIPLoader type for Wan Models

Must use "wan", NOT "default":
```python
"widgets_values": ["umt5_xxl_fp8_e4m3fn_scaled.safetensors", "wan"]
```

Valid types: stable_diffusion, sd3, wan, ltxv, flux2, hunyuan_image, qwen_image, etc.

### 4. ALL Node Inputs Must Have Link References

If input has "link": null, ComfyUI rejects with "Required input is missing". Fix:

```python
link_map = {(l[3], l[4]): l[0] for l in links}
for nd in nodes:
    for inp in nd.get("inputs", []):
        if inp.get("link") is None:
            slot_idx = nd["inputs"].index(inp)
            key = (nd["id"], slot_idx)
            if key in link_map:
                inp["link"] = link_map[key]
```

### 5. ImageResizeKJv2 keep_proportion

"disabled" is NOT valid. Use: stretch, resize, pad, pad_edge, pad_edge_pixel, crop, pillarbox_blur, total_pixels

### 6. PathchSageAttentionKJ needs sageattention pip package

If not installed, remove the node. LoRA -> BlockSwap direct connection works fine.

## VRAM Planning (14B fp8, BlockSwap, 81 frames)

| Resolution | Tokens | Peak VRAM |
|-----------|--------|-----------|
| 640x384 | 311K | ~18 GB |
| 832x480 | 505K | ~20 GB (BEST) |
| 960x544 | 661K | ~21.5 GB |
| 1024x576 | 755K | ~23 GB (OOM) |
| 1280x720 | 1.18M | ~28 GB (NO) |

Frame count impact at 832x480:
- 49 frames (3s): ~19 GB
- 81 frames (5s): ~20 GB
- 96 frames (6s): ~21 GB
- 121 frames (7.5s): ~21.5 GB

BlockSwap saves ~6 GB by loading model weights in chunks.

## KSampler Settings

With 4-step LoRA (fast):
- Stage1: steps=8, cfg=2.5, euler, simple, denoise=1.0
- Stage2: steps=6, cfg=1.5, euler, simple, denoise=1.0
- LoRA strength: 0.8 (1.0 causes artifacts)

Without LoRA (high quality, slow):
- Stage1: steps=20-30, cfg=4-6
- Stage2: steps=10-15, cfg=2-3

## Complete Node Chain

UNETLoader(H) -> LoraLoaderModelOnly -> wanBlockSwap -> KSampler(H)
UNETLoader(L) -> LoraLoaderModelOnly -> wanBlockSwap -> KSampler(L)
CLIPLoader(wan) -> CLIPTextEncode(+) -> WanFirstLastFrame -> KSampler
CLIPLoader(wan) -> CLIPTextEncode(-) -> WanFirstLastFrame -> KSampler
VAELoader -> WanFirstLastFrame + VAEDecode
CLIPVisionLoader -> CLIPVisionEncode(首) -> WanFirstLastFrame
CLIPVisionLoader -> CLIPVisionEncode(尾) -> WanFirstLastFrame
LoadImage(首) -> WanFirstLastFrame + CLIPVisionEncode
LoadImage(尾) -> WanFirstLastFrame + CLIPVisionEncode
KSampler(H) -> KSampler(L) -> VAEDecode -> VHS_VideoCombine

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| CONDITIONING mismatch LATENT | WanFL slot 0 = CONDITIONING | Connect to slot 2 |
| format False not in list | VHS is list not dict | Use dict format |
| No module sageattention | Missing pip package | Remove node or pip install |
| type default not in list | CLIPLoader wrong type | Use \"wan\" |
| Required input missing anything | PurgeVRAM needs input | Remove or connect |
| keep_proportion disabled invalid | Wrong ImageResize value | Use \"stretch\" |
| Required input missing: images | input `link` is null | Run link_map fixer (see #4 above) |

## 720p Output: Lanczos Upscale

Native 720p (1280x720) needs ~28GB VRAM. Solution: generate at 832x480, upscale with ImageResizeKJv2:

```
KSampler -> VAEDecode -> ImageResizeKJv2(1280, 720, "lanczos", "stretch") -> VHS_VideoCombine
```

- Upscale ratio 1.54x is acceptable for Lanczos
- Total VRAM: ~21GB (832x480 generation + upscale)
- Output looks sharp at 720p

## First-Last Frame Quality Rules

The #1 cause of bad output is input images that are too different.

**Golden rule: Same background, only change action.**

| Good | Bad |
|------|-----|
| Same room, cat sits→stands | Cat in room → cat in garden |
| Same angle, face looks left→right | Front view → side view |
| Same lighting, pose changes | Daylight → nighttime |

If frames differ >30%, the model "hallucinates" intermediate frames → blurry/distorted output.

**Denoise adjustment:**
- denoise=1.0: Full animation (big pose change, same background)
- denoise=0.85: Conservative (medium change)
- denoise=0.7: Subtle (small movements, very stable)

## LoRA Strength Tuning

- strength=1.0: Maximum speed but causes rough/artifacty frames
- strength=0.8: **Recommended** — keeps speed, much cleaner output
- strength=0.5: Slower (needs more steps) but highest quality with LoRA
- strength=0: No LoRA — use 20-30 steps for best quality (10+ min generation)

## Transition Prompt (关键!)

WanFirstLastFrameToVideo 的 positive 提示词必须描述首帧到尾帧之间的动作过渡, 不是画面描述!

```
❌ "smooth animation, detailed, cinematic"  ← 太泛, 模型不知道做什么
✅ "The cat gradually stands up from sitting, stretching paws forward, same background"
```

每个 Shot 应有自己的 transition_prompt:
- Shot1: "猫从坐着逐渐站起来, 伸展前爪"
- Shot2: "猫转身跳下窗台, 走向地板"

三要素缺一不可:
1. CLIPVision(首帧) → 模型知道起点
2. CLIPVision(尾帧) → 模型知道终点
3. transition_prompt → 模型知道怎么走过去

## 4-Step LoRA Slow Motion Fix

lightx2v 4-step LoRA 会导致视频慢动作。修复方法:

使用 PainterLongVideo 节点的 `motion_amplitude` 参数:
- 1.0 = 正常速度
- 1.15 = 推荐 (修复慢动作)
- 2.0 = 最大加速

插件: `git clone https://github.com/princepainter/ComfyUI-PainterLongVideo.git`

## Qwen Image Edit Pitfalls

### pixel offset bug
ComfyUI 内置 TextEncodeQwenImageEditPlus 有强制缩放导致像素偏移。
使用 `comfyui_qwen_image_edit_adv` 替代:
```
git clone https://github.com/lenML/comfyui_qwen_image_edit_adv.git
```
推荐参数: Resolution=1024, Alignment=32, CFG=1.0-2.5

### parameter name is image1 not image
TextEncodeQwenImageEditPlus 的图片参数名是 `image1`, 不是 `image`。
写 JSON 时: `"inputs": {"image1": ["node_id", 0]}` 而非 `"image": ...`

## Essential Plugins (安装到 custom_nodes/)

```bash
cd F:\Comfyui\ComfyUI-aki-v3\ComfyUI\custom_nodes

# 全家桶 (26个节点: PainterLongVideo + 音频驱动 + Qwen编辑)
git clone https://github.com/princepainter/ComfyUI-PainterNodes.git

# Qwen偏移修复 + 多图编辑
git clone https://github.com/lenML/comfyui_qwen_image_edit_adv.git

# AI视频拼接 (VACE过渡帧)
git clone https://github.com/stuttlepress/ComfyUI-Wan-VACE-Video-Joiner.git

# 3D机位选择 (96种角度)
git clone https://github.com/NickPittas/ComfyUI_CameraAngleSelector.git

# 提示词自动改写
git clone https://github.com/lihaoyun6/ComfyUI-QwenPromptRewriter.git

# LLM集成 (Ollama/Claude/GPT)
git clone https://github.com/heshengtao/comfyui_LLM_party.git
```

重启 ComfyUI 后生效。
