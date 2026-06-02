---
name: "dynamic-workflows"
description: "Dynamic Workflows — 亚希多 Agent 编排系统，基于 Claude Code Dynamic Workflows 设计"
version: "1.0.0"
author: "亚希"
created: "2026-06-01"
---

# Dynamic Workflows Skill

## 📌 概述

Dynamic Workflows 是亚希的多 Agent 编排系统，灵感来自 Claude Code 的 Dynamic Workflows 功能。

### 核心特性
- **智能任务拆分**: 自动分析任务复杂度，决定是否拆分
- **Agent Registry**: 注册不同类型的 Agent（研究、编码、分析、创意）
- **并行调度**: 使用 `sessions_spawn` 并行执行子任务
- **结果协调**: 合并所有子任务结果，生成最终报告

---

## 🔧 使用方法

### 基本用法
```python
# 触发 Dynamic Workflows
dynamic_workflow("研究 2026 年最新的 AI Agent 框架，并生成对比报告")
```

### 高级用法
```python
# 指定 Agent 类型
dynamic_workflow(
    task="研究 MCP 协议",
    agents=["research", "analysis"],
    parallel=True
)
```

---

## 🎯 适用场景

### 适合使用 Dynamic Workflows 的场景
- 大型重构任务
- 多文件迁移
- 批量测试修复
- 需要并行处理的任务
- 复杂的研究任务

### 不适合使用 Dynamic Workflows 的场景
- 简单问答
- 单一任务
- 无需并行的任务

---

## 📊 工作流程

```
用户请求
    ↓
分析任务复杂度 (1-10)
    ↓
复杂度 > 3 ?
    ├─ 否 → 直接执行
    └─ 是 → 拆分子任务
              ↓
         选择 Agent 类型
              ↓
         并行执行
              ↓
         协调结果
              ↓
         输出最终报告
```

---

## 🔍 Agent 类型

### Research Agent (研究 Agent)
- **职责**: 联网搜索、信息收集、知识整理
- **工具**: Bing 搜索、网页抓取、文件读写
- **适用**: 搜索最新技术动态、收集行业信息

### Coding Agent (编码 Agent)
- **职责**: 代码生成、调试、优化
- **工具**: 文件读写、PowerShell、Git
- **适用**: 生成代码片段、修复 bug

### Analysis Agent (分析 Agent)
- **职责**: 数据处理、统计分析、报告生成
- **工具**: 文件读写、数据处理
- **适用**: 分析日志数据、生成统计报告

### Creative Agent (创意 Agent)
- **职责**: 内容创作、文案撰写、设计
- **工具**: 文件读写、图像生成
- **适用**: 撰写文章、生成创意内容

---

## 📈 性能优化

### 并行执行
- 使用 `sessions_spawn` 并行执行子任务
- 避免串行等待，提升效率

### 任务拆分策略
- 按句号、逗号拆分
- 保持子任务粒度适中
- 避免过度拆分

### 结果协调
- 合并所有子任务结果
- 生成结构化报告
- 处理冲突和依赖

---

## ⚠️ 注意事项

1. **成本**: 多 agent 并行会增加 token 消耗
2. **协调**: 需要处理子 agent 间的依赖关系
3. **错误处理**: 单个 agent 失败不应影响整体
4. **监控**: 使用 `/workflows` 查看运行状态

---

## 📚 参考

- **Claude Code Dynamic Workflows**: v2.1.154 (May 28, 2026)
- **LearnAgent.org**: https://learnagent.org/library/updates/claude-code-latest-updates/
- **Agent Registry**: `skills/dynamic-workflows/AGENT-REGISTRY.md`

---

## 🚀 快速开始

### 步骤 1: 理解任务
分析用户请求，判断是否需要 Dynamic Workflows

### 步骤 2: 评估复杂度
使用 `analyze_complexity()` 函数评估任务复杂度

### 步骤 3: 拆分任务
如果复杂度 > 3，使用 `decompose_task()` 拆分子任务

### 步骤 4: 选择 Agent
使用 `select_agent_type()` 为每个子任务选择 Agent 类型

### 步骤 5: 并行执行
使用 `sessions_spawn` 并行执行所有子任务

### 步骤 6: 协调结果
合并所有子任务结果，生成最终报告

---

**版本**: 1.0.0
**最后更新**: 2026-06-01
**状态**: 可用
