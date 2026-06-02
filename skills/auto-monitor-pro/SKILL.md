---
name: auto-monitor-pro
description: 增强型主动监控系统。具备自愈能力，自动修复常见故障，智能路由failover，实时守护 OpenClaw 和模型服务。
version: 2.0
---

# Auto Monitor Pro

**增强版主动监控 + 自愈系统**

## 核心能力

1. **网关守护** — 检测 OpenClaw Gateway 存活状态
2. **模型监控** — Ollama (WSL2)、MiniMax、NVIDIA API 可用性
3. **自愈引擎** — 常见故障自动修复
4. **智能路由** — 模型 fail 时自动切换 fallback
5. **主动告警** — 发现问题立即通知

---

## 检查项目

### 网关健康
```
- Gateway 进程存活？
- 端口 18789 可连接？
- 最近一次响应时间
```

### 模型可用性
```
- Ollama (WSL2): 127.0.0.1:11434
- MiniMax API: api.minimax.io
- NVIDIA API: build.nvidia.com
```

### 系统资源
```
- 磁盘使用率
- 内存使用率
- CPU 负载
```

### 自愈规则
```
| 故障 | 检测方式 | 自动修复 |
|------|----------|----------|
| Ollama 无响应 | curl 127.0.0.1:11434 | 重启 WSL2 Ollama 服务 |
| Gateway 无响应 | curl 127.0.0.1:18789 | 重启 Gateway |
| MiniMax 超时 | API 请求失败 | 切换到 Ollama fallback |
| NVIDIA 超时 | API 请求失败 | 切换到 Ollama fallback |
```

---

## 故障等级

### 🔴 严重（立即告警 + 自动修复）
- Gateway 完全无响应
- 所有模型都不可用
- 磁盘 > 90%

### 🟡 警告（记录 + 尝试修复）
- 单个模型不可用
- 内存 > 85%
- CPU > 80%

### 🟢 正常（静默）
- 所有检查通过
- 只记录关键指标

---

## 使用方式

### 手动触发检查
```
/monitor
```

### 查看状态
```
/health
```

### 启用自动守护（建议开启）
```
/monitor --auto
```

---

## 输出格式

### 正常汇报
```
✅ [19:30] 系统正常
  - Gateway: ✅ 响应 12ms
  - Ollama: ✅ qwen3.5:9b 可用
  - MiniMax: ✅ M2.7 可用
  - 内存: 67% | 磁盘: 45%
```

### 异常告警
```
🚨 [19:30] 异常检测
  - Ollama: ❌ 无响应
  - 尝试修复: 重启 WSL2 Ollama... ✅ 已恢复
  - MiniMax: ⚠️ 超时 (3s)
  - 已切换至: qwen3.5:9b
```

---

## 自愈流程

```
检测到故障
    ↓
判断等级（严重/警告）
    ↓
尝试自动修复（最多3次）
    ↓
修复成功？ → 更新状态 → 记录日志
    ↓ 否
发送告警给用户
    ↓
等待人工介入
```

---

## 配置

### 告警阈值
```json
{
  "disk_warning": 80,
  "disk_critical": 90,
  "memory_warning": 85,
  "memory_critical": 95,
  "cpu_warning": 80,
  "cpu_critical": 95,
  "model_timeout": 5000,
  "gateway_timeout": 3000
}
```

### Fallback 优先级
```json
{
  "default": ["ollama/qwen3.5:9b", "ollama/gemma4:26b"],
  "reasoning": ["ollama/deepseek-r1:32b", "ollama/deepseek-r1:8b"],
  "fast": ["ollama/qwen2.5:7b", "ollama/qwen2.5:14b"]
}
```

---

## 日志

- 检查日志: `memory/monitor-YYYY-MM-DD.md`
- 故障记录: `memory/monitor-errors.md`
- 每次自愈成功都会记录

---

*最后更新: 2026-04-10*
