---
name: credential-pool
description: |
  API Key 轮换池，支持多个 API Key 轮流使用，避免单 Key 限流。
  借鉴 Hermes Agent 的 CredentialPool 最佳实践。
  使用场景：当某个 API Key 触发限流时，自动切换到下一个可用 Key。
---

# Credential Pool

## 核心功能

- **多 Key 管理**：支持多个 API Key 组成池子
- **自动轮换**：当 Key 触发限流时自动切换
- **健康追踪**：记录每个 Key 的健康状态（成功/失败/限流）
- **Jitter 退避**：并发请求不会都打在同一个 Key 上

## 使用方式

```json
// pool.config.json
{
  "providers": {
    "minimax": {
      "keys": [
        { "id": "key1", "key": "sk-xxx...", "weight": 1 },
        { "id": "key2", "key": "sk-yyy...", "weight": 1 }
      ]
    },
    "openrouter": {
      "keys": [
        { "id": "or-key1", "key": "sk-or-...", "weight": 2 }
      ]
    }
  }
}
```

```bash
# 报告 Key 健康状态
/credential-pool status

# 标记某个 Key 需要轮换
/credential-pool rotate minimax key1

# 获取当前可用 Key
/credential-pool get minimax
```

## 健康状态

| 状态 | 说明 |
|------|------|
| `healthy` | 正常使用 |
| `rate_limited` | 被限流，临时禁用 |
| `exhausted` | 配额耗尽，长时间禁用 |
| `error` | 错误过多 |

## 轮换策略

1. **权重随机**：按权重分配请求，避免单 Key 过载
2. **故障隔离**：失败的 Key 自动降低权重
3. **恢复检测**：定期尝试被禁用的 Key，看是否恢复

## 与 OpenClaw 集成

在 `openclaw.json` 中配置多个 API Key，
通过环境变量或配置文件实现自动轮换。
