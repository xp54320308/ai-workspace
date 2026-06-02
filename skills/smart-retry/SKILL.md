# Smart Retry Skill

## 定位
当 MiniMax 等 API 模型超时时，自动重试 + 智能降级。不依赖 OpenClaw 核心修改。

## 工作原理

### 重试策略
```
MiniMax 超时
  └─ 第1次重试（等待2s）
       ├─ 成功 → 继续
       └─ 失败 → 第2次重试（等待4s）
            ├─ 成功 → 继续
            └─ 失败 → 降级到 Ollama
                 ├─ Ollama 成功 → 继续
                 └─ Ollama 失败 → 降级到 qwen3.5
```

### 可降级模型
| 模型 | 用途 | 超时阈值 |
|------|------|----------|
| `minimax/MiniMax-M2.7` | 主力（复杂任务） | 45s |
| `ollama/gemma4:26b` | 中等任务 | 30s |
| `ollama/qwen3.5:9b` | 简单任务 | 20s |
| `ollama/qwen2.5:7b` | 兜底 | 15s |

## 使用方式

### 手动测试
```
/retry-test "解释量子计算"
```

### 查看当前状态
```
/retry-status
```

### 强制降级
```
/retry-force-ollama
```

## 实现

依赖 OpenClaw 内置 fallback 机制，skill 只负责：
1. 监测超时错误类型
2. 触发分级重试
3. 记录降级日志

## 状态
规划中，优先级：中
