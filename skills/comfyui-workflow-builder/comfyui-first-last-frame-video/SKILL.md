---
name: comfyui-first-last-frame-video
description: Build ComfyUI first-last frame video workflows with Wan2.2 I2V, troubleshoot common validation errors.
---

# ComfyUI 首尾帧视频工作流搭建指南

## 工作流架构 (Wan2.2 I2V 首尾帧)

```
首帧.png → CLIPVisionEncode ─┐
                             ├→ WanFirstLastFrameToVideo → Latent
尾帧.png → CLIPVisionEncode ─┘       ↓
正/负向提示词(transition_prompt) → Latent ↓
          ↓
UNET_H → LoRA → BlockSwap → Stage1 (High Noise, 20步)
          ↓
UNET_L → LoRA → BlockSwap → Stage2 (Low Noise, 10步)
          ↓
VAEDecode → ImageResize → VHS_VideoCombine (MP4)
```

## 模型需求

- wan2.2_i2v_high_noise_14B_fp8_scaled → models/diffusion_models/ (NOT unet/)
- wan2.2_i2v_low_noise_14B_fp8_scaled → models/diffusion_models/
- umt5_xxl_fp8_e4m3fn_scaled → models/text_encoders/
- wan_2.1_vae → models/vae/
- clip_vision_h → models/clip_vision/
- wan2.2_i2v_lightx2v_4steps_lora_v1_high/low → models/loras/

## 常见坑点 (必读!)

### 1. CLIPLoader type 必须是 wan 不是 default
```python
{"type": "wan"}  # correct
{"type": "default"}  # error
```

### 2. TextEncodeQwenImageEditPlus 参数名是 image1 不是 image
```python
"inputs": {"image1": [node_id, slot]}  # correct
"inputs": {"image": [node_id, slot]}  # error: got an unexpected keyword argument 'image'
```

### 3. VHS_VideoCombine widgets 是字典格式不是列表
```python
"widgets_values": {
    "frame_rate": 16,
    "loop_count": 0,
    "format": "video/h264-mp4",
    "pix_fmt": "yuv420p",
    "crf": 19,
    "save_metadata": True
}
```
loop_count 是 int，不是 None。

### 4. KSampler latent_image 类型匹配
WanFirstLastFrameToVideo 的 slot 0 是 CONDITIONING, slot 2 才是 LATENT。

### 5. SageAttention 需要安装 sageattention 包
没有就别用 PathchSageAttentionKJ 节点。

### 6. WanFirstLastFrameToVideo 三要素缺一不可
- CLIPVision 编码首帧 (起点)
- CLIPVision 编码尾帧 (终点)  
- transition_prompt (中间怎么过渡)

### 7. 4步LoRA导致慢动作
motion_amplitude=1.15 可修复，或使用 PainterLongVideo 节点。

### 8. Qwen Image Edit 像素偏移
使用 comfyui_qwen_image_edit_adv 插件替代内置 TextEncodeQwenImageEdit。

## 显存优化 (RTX 5090 23GB)
- BlockSwap ~6GB
- fp8 量化 ~50%体积
- 两阶段分离加载 ~13GB

## 推荐插件
- ComfyUI-PainterNodes (26节点全家桶)
- comfyui_qwen_image_edit_adv (Qwen偏移修复)
- ComfyUI-Wan-VACE-Video-Joiner (AI转场)
