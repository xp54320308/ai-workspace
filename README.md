# 🤖 RAG 智能知识库 v3.0

基于 Python + LangChain + ChromaDB + Ollama 的本地 RAG（检索增强生成）系统。

**新增 v3.0 特性：** 外部化配置、四层测试、闭环学习（RAG + Skill）、Tier 0/1/2 分层安装。

## 项目结构

```
RAG_Project/
├── data/                    # 📂 知识库文档
│   ├── knowledge.txt        #   AI/RAG 基础知识
│   ├── python_guide.md      #   Python 编程指南
│   ├── chromadb_guide.txt   #   ChromaDB 使用指南
│   └── ...                  #   支持 .txt/.pdf/.md/.docx/.xlsx
├── skills/                  # 🧠 闭环学习自动保存的 Skills
│   ├── index.json           #   Skill 索引
│   └── *.md                 #   各个 Skill 文件
│
├── run_rag.py               # ⚡ 一键管理入口（CLI）
├── ingest_docs.py           # 📥 多格式文档摄入
├── vectorstore_setup.py     # 🧬 向量化存储
├── rag_chat_bot.py          # 🤖 RAG 聊天机器人（v3.0 带闭环学习）
├── auto_ingest.py           # 👀 自动文档监听（watchdog）
├── simple_rag.py            # 🧪 演示脚本
│
├── config.py                # ⚙️ 配置加载器（YAML + 环境变量）
├── config.example.yaml      # 📋 配置文件模板
├── skill_manager.py         # 🧠 闭环学习管理器
│
├── SKILL.md                 # 📖 Agent 操作手册
├── INSTALL.md               # 📦 Tier 0/1/2 安装指南
├── requirements.txt         # 📦 依赖列表
├── pytest.ini               # 🧪 测试配置
│
├── tests/                   # 🧪 四层测试套件
│   ├── test_core.py         #   第一层：单元测试（无外部依赖）
│   ├── test_format.py       #   第二层：格式验证
│   ├── test_backend.py      #   第三层：后端集成（需 Ollama）
│   └── test_e2e.py          #   第四层：端到端（需完整环境）
│
└── venv/                    # 🐍 Python 虚拟环境
```

## 快速开始（Tier 0 — 5分钟）

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 全量构建向量库
python run_rag.py rebuild

# 4. 启动聊天
python run_rag.py chat
```

详细安装指南见 [INSTALL.md](INSTALL.md)（含 Tier 1/2 高级配置）。

## 命令速查

| 命令 | 说明 |
|------|------|
| `python run_rag.py ingest` | 导入文档（不向量化） |
| `python run_rag.py build` | 增量构建向量库 |
| `python run_rag.py rebuild` | 全量重建（清空旧数据） |
| `python run_rag.py chat` | 启动聊天机器人 |
| `python run_rag.py query "问题"` | 单次查询（非交互） |
| `python run_rag.py test` | 运行管道测试 |
| `python run_rag.py status` | 查看知识库状态 |
| `python run_rag.py auto` | 启动自动文档监听 |
| `python run_rag.py skills` | 列出已保存的 Skills |
| `python run_rag.py skill-stats` | 查看 Skill 统计 |

## 聊天机器人命令

| 输入 | 说明 |
|------|------|
| `exit` / `退出` | 退出 |
| `clear` / `清空` | 清空对话记忆 |
| `sources` / `来源` | 显示上轮回答来源 |
| `save` / `保存` | 将上轮问答保存为 Skill ⭐新 |

## 支持的文件格式

| 格式 | 后端 | 依赖层级 |
|------|------|----------|
| `.txt` | TextLoader | Tier 0（内置） |
| `.md` | TextLoader | Tier 0（内置） |
| `.pdf` | PyPDFLoader | Tier 0（pypdf） |
| `.docx` | python-docx | Tier 0（python-docx） |
| `.xlsx` | openpyxl | Tier 1 |
| 扫描 PDF | PaddleOCR | Tier 2 |

## 闭环学习（RAG + Skill）

借鉴 CLI-Anything 和 Hermes Agent 的 Skill 系统：

```
用户提问 → Skill 搜索匹配 → 命中 → 直接返回答案（跳过 RAG）
                       ↓ 未命中
              RAG 检索 → LLM 生成 → 返回答案
                       ↓ 用户反馈
              保存为 Skill → 下次可直接匹配
```

**用法：**
- 聊天中输入 `save` 将上轮问答保存为 Skill
- `python run_rag.py query "问题"` 自动先搜索 Skill
- Skill 文件存储在 `skills/` 目录

## 测试

```bash
# 运行单元测试（安全，无需外部依赖）
pytest tests/ -v -m core

# 运行格式验证
pytest tests/ -v -m "core"

# 运行后端测试（需要 Ollama 运行中）
pytest tests/ -v -m backend

# 运行端到端测试（需要完整环境）
pytest tests/ -v -m e2e

# 运行全部测试
pytest tests/ -v
```

## 配置

### 方式 1：config.yaml

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml
```

### 方式 2：环境变量

```bash
export RAG_CHAT_MODEL="qwen2.5:14b"
export RAG_PERSIST_DIR="/custom/path/chroma_db"
export RAG_RETRIEVAL_K=10
```

### 方式 3：直接编辑（兼容旧代码）

`rag_chat_bot.py` 顶部的 `CONFIG` 字典仍然有效，但推荐使用 config.yaml。

## 架构设计亮点

- **工具注册模式：** 借鉴 Hermes Agent 的 `registry.register()` 模式，每个格式加载器独立可扩展
- **四层测试：** 借鉴 CLI-Anything 的测试策略 — 单元→格式→后端→端到端
- **闭环学习：** 借鉴 Hermes Agent 的 Skill 系统 + CLI-Anything 的 SKILL.md 标准
- **分层配置：** 借鉴 Agent-Reach 的 Tier 0/1/2 系统，降低首次使用门槛
- **安全设计：** 借鉴 CLI-Anything 的无 `shell=True` 原则

## Agent 集成

本项目包含 `SKILL.md`，任何兼容的 AI Agent（Hermes、Claude Code、OpenClaw）都可以自动发现和操作本项目。

## 故障排查

详见 [INSTALL.md](INSTALL.md) 的故障排查章节。

| 错误 | 解决 |
|------|------|
| `Ollama 连接失败` | `ollama serve &` |
| `向量库为空` | `python run_rag.py rebuild` |
| `gemma4:26b 崩溃` | 改用 `qwen2.5:14b` |
