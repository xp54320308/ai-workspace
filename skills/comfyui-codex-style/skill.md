# ComfyUI Codex-Style Skill

## 概述
学习自 Codex Desktop 的 ComfyUI 工作方法论。核心思路：**把 ComfyUI 当 API 服务用，把工作流当代码写，用视觉反馈闭环迭代。**

## 执行流程（6 阶段）

### Phase 1: 环境侦察
**铁律：先扫描后动手，不猜路径。**

1. 枚举 ComfyUI 根目录结构
2. 逐层扫描 `models/`（按类别：checkpoints、loras、diffusion_models、text_encoders、vae、controlnet、clip_vision、upscale_models 等）
3. 扫描 `custom_nodes/` 和 `custom_nodes_disabled/`
4. 扫描 `user/default/workflows/` 和 `blueprints/`
5. 用关键词搜索（rg 或 Select-String）：wan2.2、flux、svd_xt、VideoCombine、Wan 等
6. 生成 `model_inventory.csv`（类别、文件名、大小、路径）

### Phase 2: 模型与节点分析
1. 读取已有工作流 JSON，理解节点连接方式
2. 在 `.py` 文件中搜索 `NODE_CLASS_MAPPINGS` 判断已安装节点
3. 检查节点的 `requirements.txt` 和 `install.py`
4. 评估可用模型与目标任务的匹配度

### Phase 3: 缺失节点自动补装
```powershell
# 发现缺失节点 → 直接 clone
git clone <repo_url> <comfyui_path>/custom_nodes/<node_name>

# 用 ComfyUI 自带 Python 运行安装脚本
& '<comfyui_python_path>' '<node_dir>/install.py'
```

### Phase 4: 编程式工作流构建
**关键差异：不在 GUI 拖节点，用代码构建工作流。**

1. 读取已有工作流 JSON 作为模板
2. 用 Python 脚本编程式修改节点参数（连接、模型路径、采样参数等）
3. 输出为 `wf_*.json` 文件
4. 编写 `run_*.py` 脚本串联整个流水线
5. 版本迭代：每次改一个变量，递增版本号（v45 → v79）

**Python 脚本结构模板：**
```python
import json
import urllib.request
import time

# 1. 加载工作流模板
with open('wf_source.json', 'r') as f:
    workflow = json.load(f)

# 2. 修改节点参数（按需）
# workflow['node_id']['inputs']['param'] = value

# 3. 提交到 ComfyUI API
payload = json.dumps({"prompt": workflow}).encode()
req = urllib.request.Request('http://127.0.0.1:8188/prompt', data=payload)
resp = urllib.request.urlopen(req)
prompt_id = json.loads(resp.read())['prompt_id']

# 4. 轮询等待完成
while True:
    time.sleep(10)
    queue = json.loads(urllib.request.urlopen('http://127.0.0.1:8188/queue').read())
    running = [t for t in queue.get('queue_running', []) if t[1] == prompt_id]
    pending = [t for t in queue.get('queue_pending', []) if t[1] == prompt_id]
    if not running and not pending:
        break
```

### Phase 5: ComfyUI API 提交执行
```powershell
# 提交工作流
$body = @{prompt = $workflow} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri 'http://127.0.0.1:8188/prompt' -Method Post -Body $body

# 轮询队列状态
Invoke-RestMethod -Uri 'http://127.0.0.1:8188/queue'

# 检查系统状态
Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats'
```

### Phase 6: 视觉反馈与迭代
1. 检查生成的图片/视频输出
2. 分析质量（人物一致性、运动流畅度、画面清晰度等）
3. 修改参数 → 递增版本号 → 重新执行
4. 记录每次迭代的变更原因

## 迭代管理规范
- 文件命名：`run_<项目>_v<版本号>_<变更描述>.py`
- 每个版本只改一个变量（motion、camera、pose、resolution 等）
- 保留所有版本，不要覆盖（方便回溯）
- 成功的工作流固化为模板

## ComfyUI API 端点参考
| 端点 | 方法 | 用途 |
|------|------|------|
| `/prompt` | POST | 提交工作流 |
| `/queue` | GET | 查看队列状态 |
| `/system_stats` | GET | 系统/GPU 状态 |
| `/history` | GET | 执行历史 |
| `/view` | GET | 获取生成的图片 |

## 深层架构细节（从 Codex 实际代码学到）

### Python 脚本架构
Codex 的脚本不是一次性脚本，而是**模块化可复用的代码库**：

```python
# 1. ExternalComfyServer 类 — 封装 API 通信
class ExternalComfyServer:
    def __init__(self, port): ...
    def api_get(self, path): ...    # GET /system_stats, /queue, /history
    def api_post(self, path, payload): ...  # POST /prompt

# 2. queue_and_wait() — 轮询等待完成
# 用 /history/{prompt_id} 而不是 /queue
# 超时设置 14400 秒（4小时）

# 3. 模块化复用
import run_manga_5s_pipeline_v52_fun_inpaint_character_first as base
import run_manga_30s_v62_script_to_video as v62
# v79 直接复用 v52 和 v62 的函数
```

### 工作流 JSON 构建模式
Codex 不是读取现成工作流，而是**编程式组装节点图**：

```python
def build_prompt(start_name, shot_prompt, seed, cfg):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {...}},
        "2": {"class_type": "CLIPLoader", "inputs": {...}},
        "3": {"class_type": "VAELoader", "inputs": {...}},
        "4": {"class_type": "LoadImage", "inputs": {...}},
        # ... KSampler, VAEDecode, SaveImage 等
    }
```

### 分镜脚本结构（30秒漫剧）
每个 SHOT 定义：
- `id`: 唯一标识（shot01_window_first_meet）
- `time`: 时间段（"0-5s"）
- `start` / `end`: 首尾帧描述
- `image_prompt`: 图像生成提示词
- `video_prompt`: 视频生成提示词
- `seed`: 固定种子（可复现）

### 模型搭配方案（从实际代码学到）
| 用途 | 模型 | 说明 |
|------|------|------|
| 图像生成 | Qwen Image Edit 2509 + LoRA 多角度一致性 + LoRA 4步加速 | 保持角色一致性 |
| 视频生成 | Wan 2.2 I2V 14B (high_noise + low_noise) | 双阶段采样 |
| 后处理 | RIFE 帧插值 + FFmpeg 合成 | 提升流畅度 |

### 后处理流水线（postprocess scripts）
- `decode_video()` — 用 PyAV 解码视频为帧
- `write_video()` — 用 PyAV 编码帧为视频（H.264, yuv420p）
- `build_masks()` — 用 PIL 构建区域遮罩（窗户、墙壁、座位等）
- 实现**电影级视差滚动**效果

### 关键参数（从实际配置学到）
- 分辨率：832x480（16:9 横屏）
- FPS：32.0
- 采样器：euler / simple
- 步数：4（配合 Lightning LoRA）
- CFG：5.2 ~ 5.5（分镜间微调）
- 降噪：1.0（全生成）
- Wan 2.2 I2V：121 帧 at 832x480

## 工作流模板库

从 Codex 会话中提取的完整可复用工作流 JSON：

| 文件 | 用途 | 核心节点 |
|------|------|----------|
| `wan22_i2v_dual_stage_first_last.json` | Wan 2.2 首尾帧I2V（双阶段采样） | UNETLoader×2 + KSamplerAdvanced×2 + WanFirstLastFrameToVideo |
| `wan22_fun_camera_i2v.json` | Wan 2.2 Fun Camera 运镜I2V | ADE_CameraPoseCombo + WanVideoFunCameraEmbeds + WanVideoSampler |
| `sd15_t2i_start_candidates.json` | SD 1.5 文生图（批量候选帧） | CheckpointLoaderSimple + KSampler + EmptyLatentImage(batch=4) |
| `qwen_image_edit_keyframes.json` | Qwen 多角度一致性关键帧 | TextEncodeQwenImageEditPlus + LoraLoaderModelOnly×2 |
| `video_concat.json` | 视频拼接 | LoadVideo + GetVideoComponents + ImageBatch + CreateVideo |
| `rife_2x_32fps.json` | RIFE 帧插值 2x→32fps | RIFE VFI + VHS_VideoCombine |

## 与我的 OpenClaw 集成
- 可以用 `exec` 调用 PowerShell 执行上述命令
- 可以用 `image` 工具检查生成结果
- 可以把成功的流水线保存为 OpenClaw Skill
- 可以用 cron 定时触发批量生产
