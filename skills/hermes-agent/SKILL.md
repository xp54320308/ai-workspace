# SKILL.md — Hermes Agent（NousResearch）vs OpenClaw 对比研究

## 这是什么

Hermes Agent = NousResearch 出品的自进化 AI Agent，GitHub：https://github.com/NousResearch/hermes-agent

**定位**：OpenClaw 的直接竞争对手，有 OpenClaw 迁移路径（`hermes claw migrate`）。

---

## 核心架构对比

| 组件 | OpenClaw | Hermes Agent |
|------|----------|--------------|
| 核心入口 | Gateway + 会话 | `run_agent.py` (AIAgent) |
| 会话存储 | 自身管理 | SQLite + FTS5（`hermes_state.py`） |
| Skill 系统 | `skills/*.md` | `skills/` + `/skills` Hub |
| 工具注册 | 各工具文件 | `tools/registry.py`（集中注册） |
| MCP | `windows-mcp`（stdin） | 原生 MCP Client（stdio/HTTP） |
| 模型路由 | `router.config.json` | `smart_model_routing.py`（关键词驱动） |
| Gateway | 消息通道（飞书等） | 多平台：Telegram/Discord/Slack/WhatsApp/Signal |
| 记忆 | `memory/*.md`（文件） | MemoryProvider 抽象层（可插拔） |
| 子 Agent | `sessions_spawn` | `delegate_tool.py`（RPC 子进程） |
| 定时任务 | cron | 内置 cron（`cron/`） |

---

## Hermes 核心亮点（OpenClaw 可借鉴）

### 1. Smart Model Routing（智能路由）

`agent/smart_model_routing.py`

```python
# 简单任务 → 自动切换便宜模型
_COMPLEX_KEYWORDS = {
    "debug", "implement", "refactor", "analyze", "architecture",
    "delegate", "subagent", "cron", "docker", "test", "plan"
}
# 条件：文本<160字符, 无代码块, 无URL, 无复杂关键词
```

→ **OpenClaw 启示**：我可以写一个类似的自动路由技能，根据任务复杂度选择 Ollama 免费模型或 MiniMax。

### 2. Memory Provider 抽象层

`agent/memory_manager.py` — 支持多个内存 Provider 插拔：

```python
# 预取（给 AI 参考用，加 <memory-context> 围栏防止误判）
context = prefetch_all(query)
# 同步（每次对话后写入）
sync_all(user_msg, assistant_response)
# 钩子：on_turn_start, on_session_end, on_pre_compress, on_delegation
```

→ **OpenClaw 启示**：我目前的 `memory/*.md` 系统可以升级成这种 Provider 模式。

### 3. Skill 条件系统

`agent/skill_utils.py` — 比我目前的 skill 复杂得多：

```yaml
# 声明依赖工具集
metadata:
  hermes:
    requires_toolsets: [github, web]
    fallback_for_toolsets: []
    config:          # skill 可声明需要的 config.yaml 参数
      - key: wiki.path
        default: "~/wiki"
```

### 4. MCP Client 原生支持

`tools/mcp_tool.py` — Hermes 自带 MCP 客户端（不依赖 windows-mcp）：

- 支持 stdio 和 HTTP/SSE 两种传输
- 自动重连（指数退避）
- Sampling（Server 可以反过来调用 LLM）
- 配置在 `config.yaml` 的 `mcp_servers` 下

→ **OpenClaw 启示**：windows-mcp 是类似的，但 Hermes 的配置更标准化。

### 5. Trajectory 压缩（研究用）

`trajectory_compressor.py` — 保存对话轨迹，用于训练下一代工具调用模型。

→ **目前超纲**，但说明 Hermes 不只是 AI 应用，还是 AI 研究工具。

---

## Hermes 技能列表（skills/）

内置技能目录（按类别）：

| 类别 | 技能 |
|------|------|
| autonomous-ai-agents | 自进化 Agent 相关 |
| devops | Docker, K8s, 环境管理 |
| mcp | MCP 服务器配置（mcporter + native-mcp） |
| productivity | 通用效率工具 |
| research | 研究工具 |
| smart-home | 家庭自动化 |

**optional-skills/mcp/** — MCP 专项：
- `autonomous-ai-agents`, `blockchain`, `communication`, `creative`
- `devops`, `email`, `health`, `mlops`, `productivity`, `research`, `security`

---

## OpenClaw 迁移到 Hermes

```bash
hermes claw migrate   # 官方迁移命令
```

路径：`agent/copilot_acp_client.py`（支持 ACP 协议，即 OpenClaw 的 Agent Protocol）

---

## 关键文件索引

| 文件 | 作用 |
|------|------|
| `run_agent.py` | AIAgent 核心类，chat() 方法 |
| `model_tools.py` | 工具编排，handle_function_call() |
| `agent/prompt_builder.py` | System prompt 组装 |
| `agent/context_compressor.py` | 自动上下文压缩 |
| `agent/memory_manager.py` | 内存 Provider 管理器 |
| `agent/smart_model_routing.py` | 智能路由 |
| `tools/mcp_tool.py` | MCP 客户端（1050行） |
| `tools/delegate_tool.py` | 子 Agent 委托 |
| `gateway/run.py` | Gateway 主循环 |
| `hermes_cli/setup.py` | 交互式安装向导 |

---

## 对我的改进方向

### 短期可借鉴
1. **路由技能** → 参考 `smart_model_routing.py`，写一个 OpenClaw 技能自动判断任务复杂度
2. **Skill 增强** → 给我的 skills 加 `requires_toolsets` / `config` frontmatter
3. **记忆 Provider** → 考虑把 `memory/*.md` 改成更结构化的 Provider 模式

### 长期参考
1. Hermes 的多平台 Gateway 架构
2. Skill 自进化机制（experience → skill creation）
3. ACP 协议（OpenClaw 和 Hermes 通信标准）
