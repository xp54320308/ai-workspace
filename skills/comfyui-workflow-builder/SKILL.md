---
name: comfyui-workflow-builder
description: |
  从零搭建 ComfyUI 工作流的完整指南。涵盖 JSON 结构规范、常见坑点、
  Wan2.2 I2V 首尾帧视频生成、显存优化（BlockSwap）等实战经验。
  基于 RTX 5090 (23GB VRAM) 的实测。
---

# ComfyUI 工作流搭建指南

## JSON 结构规范

### 节点定义
```python
node = {
    "id": int,           # 唯一ID，从1开始
    "type": str,         # 节点类型名称
    "pos": [x, y],       # 画布位置
    "size": [w, h],      # 节点尺寸
    "flags": {},
    "order": int,        # 通常等于 id
    "mode": 0,           # 0=正常
    "title": str,        # 可选标题
    "widgets_values": [...],  # ⚠️ 关键！见下方
    "inputs": [{"name": str, "type": str, "link": int|null}],
    "outputs": [{"name": str, "type": str, "slot_index": int, "links": [int]}],
}
```

### 链接定义
```json
[link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
```

## ⚠️ 关键坑点（踩过才懂）

### 1. `widgets_values` 格式因节点而异

**大多数节点用列表：**
```json
"widgets_values": ["model.safetensors", "default"]
```

**VHS_VideoCombine 用字典：**
```json
"widgets_values": {
    "save_output": true,
    "filename_prefix": "输出名",
    "loop_count": 0,
    "pix_fmt": "yuv420p",
    "save_metadata": false,
    "crf": 15,
    "format": "video/h264-mp4",
    "no_preview": false,
    "frame_rate": 16,
    "pingpong": true
}
```
用列表会导致 `format: 'False' not in list` 和 `loop_count: None` 错误。

### 2. WanFirstLastFrameToVideo 输出顺序

```
output[0] = positive (CONDITIONING)
output[1] = negative (CONDITIONING)
output[2] = latent   (LATENT)      ← 不是 slot 0！
```
**常见错误：** 把 slot 0 连到 KSampler 的 `latent_image`，会报
`received_type(CONDITIONING) mismatch input_type(LATENT)`

### 3. CLIPLoader 的 type 参数

```python
# ❌ 错误
["umt5_xxl_fp8.safetensors", "default"]
# 报错: Value not in list: type: 'default' not in ['wan', 'flux2', ...]

# ✅ 正确 — Wan 模型用 "wan"
["umt5_xxl_fp8.safetensors", "wan"]
```

有效 type 值：`stable_diffusion`, `sd3`, `wan`, `flux2`, `hidream`, `chroma`, `ltxv`, ...

### 4. PurgeVRAM 节点需要输入

`LayerUtility: PurgeVRAM V2` 需要连接一个输入（`anything` 类型）才能工作。
它不能作为独立的清理节点放在流程中间。
**解决方案：** 用 `easy cleanGpuUsed` 替代，或直接不放（BlockSwap 已经够用）。

### 5. SageAttention 需要额外安装

`PathchSageAttentionKJ` 节点依赖 `sageattention` Python 包。
如果未安装会报 `No module named 'sageattention'`。
**解决方案：** 删除该节点，LoRA 直连 BlockSwap。

## Wan2.2 I2V 首尾帧工作流架构

```
首帧.png ─→ LoadImage ─→ CLIPVisionEncode ─┐
                                           ├→ WanFirstLastFrameToVideo
尾帧.png ─→ LoadImage ─→ CLIPVisionEncode ─┘       ↓
                                                slot[2]=LATENT
正向提示词 ──→ CLIPTextEncode ──→ KSampler ←───────┘
负向提示词 ──→ CLIPTextEncode ──→ KSampler
                                    ↓
                               VAEDecode → VHS_VideoCombine → MP4
```

### 模型加载链
```
UNETLoader (high_noise)
  → LoraLoaderModelOnly (lightx2v_4steps_high)
    → wanBlockSwap
      → KSampler (Stage1: 20步, cfg=4, euler, simple)

UNETLoader (low_noise)
  → LoraLoaderModelOnly (lightx2v_4steps_low)
    → wanBlockSwap
      → KSampler (Stage2: 10步, cfg=1, euler, simple, denoise=1)
```

### 必需模型
| 模型 | 目录 | 大小 |
|------|------|------|
| wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors | diffusion_models/ | 13.3 GB |
| wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors | diffusion_models/ | 13.3 GB |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | text_encoders/ | 6.3 GB |
| wan_2.1_vae.safetensors | vae/ | 0.2 GB |
| clip_vision_h.safetensors | clip_vision/ | 1.2 GB |
| wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors | loras/ | 1.1 GB |
| wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors | loras/ | 1.1 GB |

## 显存优化策略

### BlockSwap
- 把模型分成小块，只在需要时加载到 GPU
- 14B fp8 模型（13.3GB）经 BlockSwap 后峰值约 7GB

### 分辨率选择（RTX 5090, 23GB VRAM）
| 分辨率 | 帧数 | 峰值显存 | 状态 |
|--------|------|----------|------|
| 640×384 | 81 | ~18 GB | ✅ 稳定 |
| **832×480** | **81** | **~20 GB** | **⭐ 推荐** |
| 960×544 | 49 | ~20 GB | ⚠️ 帧数受限 |
| 1024×576 | - | ~23 GB | ❌ OOM |

### 两阶段采样
- Stage1 (High Noise): 20步, cfg=4, denoise=1 — 粗生成
- Stage2 (Low Noise): 10步, cfg=1, denoise=1 — 精修细节
- 两阶段不同时加载模型（BlockSwap 自动管理）

## 验证工作流

在加载到 ComfyUI 前，用 Python 做静态检查：

```python
# 链接完整性
node_ids = {n['id'] for n in nodes}
link_ids = {l[0] for l in links}
for l in links:
    assert l[1] in node_ids, f"link {l[0]}: src {l[1]} missing"
    assert l[3] in node_ids, f"link {l[0]}: dst {l[3]} missing"

# 输入引用
for n in nodes:
    for i in n.get('inputs', []):
        lr = i.get('link')
        if lr is not None:
            assert lr in link_ids, f"N{n['id']}.{i['name']}→L{lr}"
```

## 调试 ComfyUI 验证错误

| 错误信息 | 原因 | 修复 |
|----------|------|------|
| `Value not in list: type: 'X' not in [...]` | widgets_values 顺序错或值错 | 查节点定义确认正确顺序 |
| `received_type(A) mismatch input_type(B)` | 链接类型不匹配 | 检查输出 slot 顺序 |
| `format: 'False' not in list` | VHS_VideoCombine 用了列表 | 改为字典格式 |
| `loop_count: None` | VHS_VideoCombine 缺少值 | 用字典显式设置 |
| `No module named 'X'` | 缺少 Python 依赖 | 删除节点或安装依赖 |
| `Required input is missing: anything` | PurgeVRAM 需要输入 | 连接输入或删除节点 |
