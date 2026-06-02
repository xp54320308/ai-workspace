---
name: self-evolution
description: Hermes 自我进化日志 — 记录任务经验、总结教训、积累决策知识。每次任务完成后自动记录经验到 ChromaDB，遇到新任务时主动检索相关经验，形成闭环学习机制。
category: hermes-core
tags: [memory, self-improvement, chromadb, experience]
version: 1.0.0
author: Hermes
triggers:
  - 任务完成后（尤其是 cron job）应自动记录经验到 evolution log
  - 用户问"之前是怎么处理的"、"有没有类似经验"
  - 任务失败后需要总结教训
  - 定期生成分任务的进化报告（周报/月报）
  - 任何涉及 ChromaDB 持久化经验积累的场景

related_skills:
  - vector-memory-store  # 通用 ChromaDB 记忆，两者互补；self-evolution 专注任务闭环学习
  - rag-vector-store-monitor  # ChromaDB 健康监控，evolution 依赖同一数据库

when_to_use: |
  每次 cron job 执行完成后，或任何多步骤任务结束时，都应该记录一条 evolution 条目。
  当用户提到"上次就是这样失败的"、"之前遇到过吗"，应该主动 recall。
  当需要生成阶段性报告时，运行 evolution_summary.py。
  
  注意：本 skill 专注「任务经验闭环」，与 vector-memory-store（通用记忆）的分工是：
  - self-evolution = 任务级：成功/失败决策、教训、下次建议
  - vector-memory = 知识级：项目信息、工具配置、长期事实
---

# Self-Evolution Skill

## 核心理念

每次任务完成后自动记录经验到 ChromaDB，包括：成功决策、失败原因、改进建议。下次遇到类似任务时主动检索，让 Hermes 越用越聪明。

## 核心概念

**Evolution Entry（进化条目）**
```
{
  "task_type": "wechat_posting" | "research" | "code_generation" | "debug" | "...",
  "task_summary": "简短描述",
  "outcome": "success" | "partial" | "failed",
  "key_decisions": ["决定1", "决定2"],
  "what_went_well": ["做得好1", "做得好2"],
  "what_could_improve": ["改进点1", "改进点2"],
  "lessons": ["教训1", "教训2"],
  "下次遇到类似任务应该:": "具体建议",
  "timestamp": "ISO8601"
}
```

**Collection**: `hermes_evolution`（ChromaDB）
**Embedding**: nomic-embed-text（768维）

## 使用方式

### 手动记录经验
```
hermes evolution log
→ 引导式对话：询问任务类型、结果、关键决策、改进点
→ 自动存入 ChromaDB
```

### 检索相关经验
```
hermes evolution recall <任务描述>
→ 从 ChromaDB 检索最相关的历史经验
→ 以结构化格式呈现
```

### 生成进化报告
```
hermes evolution summary [days=7]
→ 汇总最近 N 天的进化条目
→ 给出趋势分析和改进建议
```

## 快速使用示例

### 记录经验（交互式）
```bash
python3 ~/.hermes/skills/self-evolution/scripts/log_evolution.py --interactive
```

### 记录经验（命令行参数）
```bash
python3 ~/.hermes/skills/self-evolution/scripts/log_evolution.py \
  --type wechat_posting \
  --summary "微信公众号每日采集发文" \
  --outcome failed \
  --decision "IP动态变化未提前感知" \
  --improve "需要固定IP或更早检查白名单"
```

### 自然语言检索（最常用）
```bash
python3 ~/.hermes/skills/self-evolution/scripts/recall_evolution.py --query "微信发文失败 IP白名单"
```

### 按类型查看最近经验
```bash
python3 ~/.hermes/skills/self-evolution/scripts/recall_evolution.py --task-type wechat_posting
```

### 生成周报
```bash
python3 ~/.hermes/skills/self-evolution/scripts/evolution_summary.py --days 7
```

### 在 cron job 中自动记录
在 job prompt 末尾添加：
```
## 任务完成后
请将本次执行结果记录到 self-evolution：
~/.hermes/skills/self-evolution/scripts/log_evolution.py \
  --type <任务类型> --summary "<描述>" --outcome <success/partial/failed> \
  --decision "<关键决策>" --improve "<改进点>" --lesson "<教训>"
```

## ChromaDB Schema

**Collection**: `hermes_evolution`
```python
embedding_function = OllamaEmbeddingFunction(
    url="http://localhost:11434",
    model_name="nomic-embed-text"
)
```

**Document 结构**: JSON序列化的Evolution Entry
**Metadata 索引**: `task_type`, `outcome`, `timestamp`

## 实现文件

- `scripts/log_evolution.py` — 记录进化条目
- `scripts/recall_evolution.py` — 检索相关经验
- `scripts/evolution_summary.py` — 生成汇总报告
