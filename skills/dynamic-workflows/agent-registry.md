# Agent Registry — 亚希多 Agent 编排系统
> 2026-06-01 | 基于 Claude Code Dynamic Workflows 设计

## 📌 架构概览

```
┌─────────────────────────────────────────────────────────┐
│              亚希 Dynamic Workflows 系统                 │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │     Orchestrator (主 Agent)     │
        │     - 分析任务复杂度            │
        │     - 自动拆分子任务            │
        │     - 选择 Agent 类型           │
        │     - 并行调度执行              │
        │     - 协调结果                  │
        └────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ 研究    │    │ 编码    │    │ 分析    │
    │ Agent   │    │ Agent   │    │ Agent   │
    └─────────┘    └─────────┘    └─────────┘
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ 联网    │    │ 代码    │    │ 数据    │
    │ 搜索    │    │ 生成    │    │ 处理    │
    └─────────┘    └─────────┘    └─────────┘
```

---

## 🔧 Agent 类型定义

### 1. Research Agent (研究 Agent)
**职责**: 联网搜索、信息收集、知识整理
**工具**: Bing 搜索、网页抓取、文件读写
**适用任务**: 
- 搜索最新技术动态
- 收集行业信息
- 整理学习笔记

### 2. Coding Agent (编码 Agent)
**职责**: 代码生成、调试、优化
**工具**: 文件读写、PowerShell、Git
**适用任务**:
- 生成代码片段
- 修复 bug
- 重构代码

### 3. Analysis Agent (分析 Agent)
**职责**: 数据处理、统计分析、报告生成
**工具**: 文件读写、数据处理
**适用任务**:
- 分析日志数据
- 生成统计报告
- 处理结构化数据

### 4. Creative Agent (创意 Agent)
**职责**: 内容创作、文案撰写、设计
**工具**: 文件读写、图像生成
**适用任务**:
- 撰写文章
- 生成创意内容
- 设计方案

### 5. General Agent (通用 Agent)
**职责**: 处理通用任务
**工具**: 所有可用工具
**适用任务**:
- 无法分类的任务
- 混合类型任务

---

## 📋 Agent 注册表

```yaml
agents:
  research:
    name: "研究 Agent"
    description: "联网搜索、信息收集、知识整理"
    tools: ["bing_search", "web_scrape", "file_read", "file_write"]
    capabilities: ["search", "summarize", "organize"]
    
  coding:
    name: "编码 Agent"
    description: "代码生成、调试、优化"
    tools: ["file_read", "file_write", "powershell", "git"]
    capabilities: ["generate", "debug", "refactor"]
    
  analysis:
    name: "分析 Agent"
    description: "数据处理、统计分析、报告生成"
    tools: ["file_read", "file_write", "data_process"]
    capabilities: ["analyze", "visualize", "report"]
    
  creative:
    name: "创意 Agent"
    description: "内容创作、文案撰写、设计"
    tools: ["file_read", "file_write", "image_generate"]
    capabilities: ["write", "design", "create"]
    
  general:
    name: "通用 Agent"
    description: "处理通用任务"
    tools: ["all"]
    capabilities: ["all"]
```

---

## 🎯 任务拆分策略

### 复杂度评估
```python
def analyze_complexity(task):
    """
    分析任务复杂度，返回 1-10 分
    """
    score = 0
    
    # 1. 任务长度
    if len(task) > 500: score += 2
    elif len(task) > 200: score += 1
    
    # 2. 关键词分析
    complex_keywords = ["研究", "分析", "设计", "重构", "迁移", "批量"]
    for keyword in complex_keywords:
        if keyword in task:
            score += 1
    
    # 3. 并行潜力
    if "多个" in task or "批量" in task or "并行" in task:
        score += 2
    
    # 4. 依赖关系
    if "然后" in task or "之后" in task or "最后" in task:
        score += 1
    
    return min(score, 10)
```

### 任务拆分
```python
def decompose_task(task, complexity):
    """
    根据复杂度拆分任务
    """
    if complexity <= 3:
        return [task]  # 简单任务不拆分
    
    # 按句号拆分
    sentences = task.split("。")
    subtasks = []
    
    for sentence in sentences:
        if len(sentence.strip()) > 10:
            subtasks.append(sentence.strip())
    
    # 如果拆分后任务太少，按逗号拆分
    if len(subtasks) < 2:
        subtasks = task.split("，")
        subtasks = [t.strip() for t in subtasks if len(t.strip()) > 10]
    
    return subtasks if len(subtasks) > 1 else [task]
```

### Agent 类型选择
```python
def select_agent_type(task):
    """
    根据任务内容选择 Agent 类型
    """
    task_lower = task.lower()
    
    # 研究类关键词
    if any(keyword in task_lower for keyword in ["搜索", "查找", "研究", "了解", "学习"]):
        return "research"
    
    # 编码类关键词
    if any(keyword in task_lower for keyword in ["代码", "编程", "实现", "修复", "调试"]):
        return "coding"
    
    # 分析类关键词
    if any(keyword in task_lower for keyword in ["分析", "统计", "数据", "报告"]):
        return "analysis"
    
    # 创意类关键词
    if any(keyword in task_lower for keyword in ["撰写", "设计", "创作", "文案"]):
        return "creative"
    
    return "general"
```

---

## 🚀 执行流程

### 完整流程
```python
def dynamic_workflow(user_request):
    """
    Dynamic Workflows 主流程
    """
    # 1. 分析任务复杂度
    complexity = analyze_complexity(user_request)
    print(f"任务复杂度: {complexity}/10")
    
    # 2. 决定是否拆分
    if complexity <= 3:
        print("简单任务，直接执行")
        return execute_single_task(user_request)
    
    # 3. 拆分子任务
    subtasks = decompose_task(user_request, complexity)
    print(f"拆分为 {len(subtasks)} 个子任务")
    
    # 4. 为每个子任务选择 Agent 类型
    task_assignments = []
    for i, task in enumerate(subtasks):
        agent_type = select_agent_type(task)
        task_assignments.append({
            "id": i + 1,
            "task": task,
            "agent_type": agent_type
        })
        print(f"  子任务 {i+1}: [{agent_type}] {task[:50]}...")
    
    # 5. 并行执行
    results = parallel_execute(task_assignments)
    
    # 6. 协调结果
    final_result = merge_results(results)
    
    return final_result
```

### 并行执行
```python
def parallel_execute(task_assignments):
    """
    并行执行所有子任务
    """
    results = []
    
    for assignment in task_assignments:
        # 使用 sessions_spawn 并行执行
        result = sessions_spawn(
            task=assignment["task"],
            taskName=f"dynamic-{assignment['agent_type']}-{assignment['id']}",
            mode="run"
        )
        results.append({
            "id": assignment["id"],
            "agent_type": assignment["agent_type"],
            "result": result
        })
    
    return results
```

### 结果协调
```python
def merge_results(results):
    """
    合并所有子任务结果
    """
    merged = {
        "summary": "",
        "details": [],
        "status": "completed"
    }
    
    for result in results:
        merged["details"].append({
            "agent_type": result["agent_type"],
            "output": result["result"]
        })
    
    # 生成摘要
    merged["summary"] = f"完成 {len(results)} 个子任务"
    
    return merged
```

---

## 📊 状态监控

### /workflows 命令
```python
def workflows_command():
    """
    显示所有 workflow 运行状态
    """
    # 获取所有子 agent 状态
    agents = subagents(action="list")
    
    print("=== Dynamic Workflows 状态 ===")
    print(f"运行中: {len([a for a in agents if a['status'] == 'running'])}")
    print(f"已完成: {len([a for a in agents if a['status'] == 'completed'])}")
    print(f"失败: {len([a for a in agents if a['status'] == 'failed'])}")
    
    for agent in agents:
        print(f"\n[{agent['status']}] {agent['taskName']}")
        print(f"  任务: {agent['task'][:100]}...")
```

---

## 🎯 实施计划

### 本周（阶段 1）
- [x] 创建 Agent Registry 文档
- [ ] 实现复杂度评估函数
- [ ] 实现任务拆分函数
- [ ] 实现 Agent 类型选择函数

### 下周（阶段 2）
- [ ] 实现并行执行函数
- [ ] 实现结果协调函数
- [ ] 创建 /workflows 命令
- [ ] 测试 Dynamic Workflows

### 本月（阶段 3）
- [ ] 优化任务拆分策略
- [ ] 添加错误处理
- [ ] 性能监控和优化
- [ ] 文档完善

---

## 📚 参考

- **Claude Code Dynamic Workflows**: v2.1.154 (May 28, 2026)
- **LearnAgent.org**: https://learnagent.org/library/updates/claude-code-latest-updates/
- **设计原则**: Orchestrator 模式、自动拆分、并行执行、结果协调

---

**最后更新**: 2026-06-01
**状态**: 实施中
