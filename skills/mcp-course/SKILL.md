# SKILL.md — MCP Course (Model Context Protocol)

## 这是什么

HuggingFace 出品的 MCP 课程，地址：https://github.com/huggingface/mcp-course

学习如何构建 MCP 服务器和客户端。

## 课程结构

```
skills/mcp-course/
├── units/en/              # 英文课程内容
│   ├── unit0/             # 入门介绍
│   ├── unit1/             # MCP 基础（概念、架构、客户端、SDK）
│   ├── unit2/             # MCP 客户端开发
│   ├── unit3/             # 构建 MCP 服务器（PR Agent）
│   └── unit3_1/           # 高级：MCP 服务器、客户端、Webhook
└── projects/              # 实战项目代码
    └── unit3/
        ├── build-mcp-server/        # PR Agent MCP 服务器
        ├── github-actions/          # GitHub Actions 集成
        ├── slack-notification/      # Slack 通知
        └── team-guidelines/         # 团队规范
```

## 核心概念速查

### MCP 架构（类比 USB-C）

| 组件 | 角色 |
|------|------|
| **Host** | 用户面向的 AI 应用（Claude Desktop、Cursor） |
| **Client** | Host 内管理到某个 Server 通信的组件（1:1 连接） |
| **Server** | 通过 MCP 协议暴露 Tools/Resources/Prompts 的外部程序 |

### M×N 问题 → MCP 解决方案

- **无 MCP**：M 个 AI App × N 个工具 = M×N 个定制集成
- **有 MCP**：M 个 AI App（实现 Client）+ N 个工具（实现 Server）= M+N 个实现

### 四大能力（Capabilities）

| 能力 | 说明 | 示例 |
|------|------|------|
| **Tools** | AI 可调用的可执行函数 | 天气查询、代码执行 |
| **Resources** | 只读数据源 | 科学论文、文档 |
| **Prompts** | 预定义模板/工作流 | 摘要生成、代码风格 |
| **Sampling** | Server 发起 LLM 交互请求 | 写作自我审查 |

### 传输类型

- **stdio**：通过标准输入/输出通信（本地进程）
- **SSE**：Server-Sent Events（远程服务）

## 快速开始：构建第一个 MCP 服务器

### 1. 安装依赖

```bash
pip install mcp
# 或使用 uv
uv add mcp
```

### 2. 创建服务器（基于 FastMCP）

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def analyze_code(code: str) -> str:
    """分析代码并返回审查意见"""
    return f"分析了 {len(code)} 行代码"

# 运行
mcp.run()
```

### 3. 配置客户端（mcp.json）

```json
{
  "servers": {
    "my-server": {
      "command": "python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## 项目模板

### PR Agent（MCP 服务器实战）

路径：`projects/unit3/build-mcp-server/`

**三个核心工具**：
1. `analyze_file_changes` — 获取 git diff 信息
2. `get_pr_templates` — 列出可用 PR 模板
3. `suggest_template` — 智能推荐 PR 模板

### Slack 通知服务器

路径：`projects/unit3/slack-notification/`

- 监听 webhook 事件
- 向 Slack 频道发送通知

### GitHub Actions 集成

路径：`projects/unit3/github-actions-integration/`

- 接收 GitHub webhook
- 自动分析 PR 内容

## SDK 选择

| SDK | 语言 | 适用场景 |
|-----|------|---------|
| **FastMCP** | Python | 快速原型、简单服务器 |
| **MCP Python SDK** | Python | 完整控制、正式项目 |
| **MCP TypeScript SDK** | TypeScript | 前端集成、Node.js |

## 学习路径

1. **unit1** — 先看 key-concepts.mdx、mcp-clients.mdx、sdk.mdx
2. **unit3/build-mcp-server** — 跟着教程构建 PR Agent
3. **unit3_1** — 深入 webhook、客户端开发

## 实用链接

- MCP 官方文档：https://modelcontextprotocol.io/
- HuggingFace MCP Server：https://huggingface.co/settings/mcp
- 官方 Discord：MCP 社区
