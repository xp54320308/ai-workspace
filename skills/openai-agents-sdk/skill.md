---
name: openai-agents-sdk
description: OpenAI Agents SDK 多智能体框架。用于构建 multi-agent 工作流、工具调用、handoffs、guardrails、sandbox。当需要构建多 agent 协作、工具编排、human-in-the-loop、structured output 时使用。Python 3.10+，由 OpenAI 官方维护，25.4k stars。
license: MIT
source: https://github.com/openai/openai-agents-python
---

# OpenAI Agents SDK

轻量但强大的多 agent 框架，支持 OpenAI Responses/Chat Completions API 及 100+ 其他 LLM 提供商。

## 核心概念速查

| 概念 | 用途 |
|------|------|
| **Agent** | LLM + 指令 + 工具 + guardrails + handoffs |
| **Runner** | 管理 agent 运行循环、turns、tools、handoffs、sessions |
| **Tool** | 函数工具、MCP 工具、Hosted 工具、计算机操作 |
| **Handoff** | agent 之间转移控制权（去中心化路由） |
| **Agents as Tools** | manager agent 持有控制权，调用 sub-agents（中心化路由） |
| **Guardrails** | 输入/输出安全检查 |
| **Sandbox Agent** | 在隔离容器中运行，可操作文件系统 |
| **Session** | 自动管理对话历史 |

## 快速上手

```python
from agents import Agent, Runner

agent = Agent(
    name="Haiku agent",
    instructions="Always respond in haiku form",
    model="gpt-5-nano",
)

result = Runner.run_sync(agent, "Explain quantum entanglement")
print(result.final_output)
```

## 两大多 agent 模式

### 1. Manager 模式（中心化）
```python
booking_agent = Agent(...)
refund_agent = Agent(...)

customer_facing_agent = Agent(
    name="Customer-facing agent",
    instructions="Handle all direct user communication.",
    tools=[
        booking_agent.as_tool(
            tool_name="booking_expert",
            tool_description="Handles booking questions.",
        ),
        refund_agent.as_tool(
            tool_name="refund_expert",
            tool_description="Handles refund questions.",
        ),
    ],
)
```
Manager 持有最终答案，可合并多个 specialist 输出。

### 2. Handoffs 模式（去中心化）
```python
booking_agent = Agent(...)
refund_agent = Agent(...)

triage_agent = Agent(
    name="Triage agent",
    instructions="Route to booking or refund agent based on user question.",
    handoffs=[booking_agent, refund_agent],
)
```
选定的 specialist 直接拥有对话控制权。

## 工具定义

```python
from agents import function_tool

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    return f"The weather in {city} is sunny"
```

## Structured Output

```python
from pydantic import BaseModel
from agents import Agent

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text",
    output_type=CalendarEvent,
)
```

## Guardrails

```python
from agents import input_guardrail, output_guardrail

@input_guardrail
async def check_relevance(context, agent, input_data):
    # 检查输入是否相关
    return InputGuardrailResult(
        pass_score=0.8,
        reasoning="The input is relevant to the task."
    )
```

## Lifecycle Hooks

```python
from agents import Agent, RunHooks, Runner

class LoggingHooks(RunHooks):
    async def on_agent_start(self, context, agent):
        print(f"Starting {agent.name}")

    async def on_agent_end(self, context, agent, output):
        print(f"{agent.name} finished with usage: {context.usage}")

agent = Agent(name="Assistant", instructions="Be concise.")
result = await Runner.run(agent, "Explain quines", hooks=LoggingHooks())
```

## Sandbox Agent

```python
from agents import Runner
from agents.run import RunConfig
from agents.sandbox import Manifest, SandboxAgent, SandboxRunConfig
from agents.sandbox.entries import GitRepo
from agents.sandbox.sandboxes import UnixLocalSandboxClient

agent = SandboxAgent(
    name="Workspace Assistant",
    instructions="Inspect the sandbox workspace before answering.",
    default_manifest=Manifest(entries={"repo": GitRepo(repo="openai/openai-agents-python", ref="main")}),
)

result = Runner.run_sync(
    agent,
    "Inspect the repo README and summarize what this project does.",
    run_config=RunConfig(sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())),
)
print(result.final_output)
```

## 关键设计原则（来自 SDK 本身）

1. **Provider-agnostic** — 不绑定 OpenAI，可接入任何 LLM
2. **LLM-driven orchestration** — 让 LLM 决定 agent 之间的路由
3. **Code-driven orchestration** — 也可以通过 structured output + code 控制流
4. **Hooks everywhere** — lifecycle hooks 可观察、可干预每个阶段

## 与 OpenClaw 的关系

OpenClaw 是**编排层**（多 channel 连接），OpenAI Agents SDK 是**多 agent 执行框架**。
可以结合使用：用 OpenClaw 连接外部世界，用 Agents SDK 处理复杂的多 agent 逻辑。

## 安装

```bash
pip install openai-agents
# 或
uv add openai-agents
```

## 源文件位置

`C:\Users\qw\.openclaw\workspace\memory\learned\openai-agents-python\`
