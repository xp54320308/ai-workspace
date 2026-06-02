---
name: error-classifier
description: |
  细粒度错误分类和恢复策略建议。借鉴 Hermes Agent 的 FailoverReason 枚举。
  使用场景：模型调用失败时，根据错误类型推荐恢复动作（重试/压缩/切换模型/轮换Key）。
  不是实际执行恢复，而是给出明确的恢复指导。
---

# Error Classifier

## 错误分类体系

**来源**：Hermes Agent `error_classifier.py` 的 FailoverReason 枚举

### 认证错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `auth` | 401/403，可刷新/轮换凭证 | rotate_key → retry |
| `auth_permanent` | 认证彻底失败 | abort |

### 计费/配额错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `billing` | 402/配额耗尽 | rotate_key → switch_provider |
| `rate_limit` | 429/限流 | backoff → retry |

### 服务器错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `overloaded` | 503/529 服务过载 | backoff → retry |
| `server_error` | 500/502 内部错误 | retry |

### 传输错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `timeout` | 连接/读取超时 | rebuild_client → retry |

### 上下文错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `context_overflow` | 上下文太长 | compress_context → retry |
| `payload_too_large` | 413 请求体太大 | compress_payload → retry |

### 模型错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `model_not_found` | 404/无效模型 | fallback_to_another_model |

### 请求格式错误
| 类型 | 说明 | 动作 |
|------|------|------|
| `format_error` | 400 格式错误 | abort 或 strip → retry |

## 中文错误支持

内置中文错误模式检测：
- `超过最大长度`
- `上下文长度`
- `token limit`

## 使用方式

```bash
/error-classifier classify "模型返回的错误信息"
```

返回结构化分析：
```
reason: context_overflow
retryable: true
should_compress: true
should_fallback: false
recovery: "上下文太长，建议压缩后重试"
```

## 恢复策略优先级

1. **可压缩** → 先压缩上下文，再重试
2. **可重试** → 抖动退避后重试
3. **可切换模型** → fallback 链
4. **可轮换 Key** → 切换 API Key
5. **中止** → 不可恢复，记录并报告

---

## 反合理化表（Anti-Rationalization）

| 借口 | 现实 |
|------|------|
| "重试一下应该就好了" | 盲目重试浪费配额。先分类错误，再决定策略 |
| "换个模型太麻烦，先等等" | 如果当前模型挂了，等 = 浪费时间 |
| "错误信息太长，不看了" | 错误详情是分类的关键依据，必须读完 |
| "这个错误以前见过，直接重试" | 同样错误码可能有不同原因，每次都重新分类 |
| "记录错误没用，下次遇到再说" | 错误模式 = 预测未来故障的依据 |

---

## 验证清单（Verification）

每次错误分类完成后，必须确认：

- [ ] 错误信息已完整读取（不是只看状态码）
- [ ] 已匹配到具体分类（`auth`/`rate_limit`/`context_overflow` 等）
- [ ] 已给出明确恢复动作（重试/压缩/切换/中止）
- [ ] 如果是新错误模式，已记录到知识库
- [ ] 恢复策略已按优先级排序

### 退出条件
**分类 + 恢复建议 + 记录（如新模式）= 完成。不分类直接重试 = 赌博。**
