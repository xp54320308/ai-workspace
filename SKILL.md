---
name: rag-pipeline
description: |
  本地 RAG（检索增强生成）知识库系统。支持 .txt/.pdf/.md/.docx/.xlsx 多格式文档摄入，
  ChromaDB 向量存储，Ollama 本地 LLM 推理，带记忆的多轮对话聊天机器人。
  自动文档监听，增量重建，闭环 Skill 学习。
---

# 🤖 RAG Pipeline — Agent 操作手册

## 快速识别

- **项目类型：** 本地 RAG 知识库系统
- **技术栈：** Python + LangChain + ChromaDB + Ollama
- **嵌入模型：** nomic-embed-text
- **Chat 模型：** qwen2.5:14b
- **向量库路径：** `chroma_db`
- **数据目录：** `data/` (项目根目录下)

## 安装

### Tier 0：零配置（5分钟启动）

```bash
cd ai-workspace
source venv/bin/activate
pip install -r requirements.txt

# 确认 Ollama 运行中
ollama list

# 全量构建 + 启动聊天
python run_rag.py rebuild
python run_rag.py chat
```

### Tier 1：多格式支持（需安装额外依赖）

```bash
# Excel 支持
pip install openpyxl>=3.1.0

# PaddleOCR（扫描 PDF 支持）
pip install paddlepaddle paddleocr

# 自动文档监听
pip install watchdog>=3.0.0
```

### Tier 2：高级配置

编辑 `config.yaml`（项目根目录）自定义所有参数。

## 命令速查表

| 命令 | 说明 | 何时使用 |
|------|------|----------|
| `python run_rag.py ingest` | 导入文档（不向量化） | 检查文档加载是否正常 |
| `python run_rag.py build` | 增量构建向量库 | 添加新文档后 |
| `python run_rag.py rebuild` | 全量重建（清空旧数据） | 首次使用、文档大量变更 |
| `python run_rag.py chat` | 启动聊天机器人 | 日常使用 |
| `python run_rag.py test` | 运行管道测试 | 验证环境是否正常 |
| `python run_rag.py status` | 查看知识库状态 | 检查当前数据量 |
| `python run_rag.py auto` | 启动自动文档监听 | 持续运行场景 |
| `python run_rag.py skills` | 列出已保存的 Skills | 闭环学习 |
| `python run_rag.py skill-stats` | 查看 Skill 统计信息 | 闭环学习 |

## 聊天机器人命令

| 输入 | 说明 |
|------|------|
| `exit` / `退出` | 退出聊天 |
| `clear` / `清空` | 清空对话记忆 |
| `sources` / `来源` | 显示上轮回答的来源文件 |
| `save` / `保存` | 将上轮问答保存为 Skill |

## 支持的文件格式

| 格式 | 后端 | 依赖 |
|------|------|------|
| `.txt` | TextLoader | 无（内置） |
| `.md` | TextLoader | 无（内置） |
| `.pdf` | PyPDFLoader | pypdf |
| `.docx` | python-docx | python-docx |
| `.xlsx` | openpyxl | openpyxl |
| 扫描 PDF | PaddleOCR | paddlepaddle + paddleocr |

## Agent 使用指南

### 查询知识库（非交互模式）

```bash
python run_rag.py query "你的问题"
```

### 检查系统健康

```bash
python run_rag.py status
```

### 全量重建（文档变更后）

```bash
python run_rag.py rebuild
```

## 关键文件说明

| 文件 | 作用 |
|------|------|
| `run_rag.py` | 一键管理入口（CLI） |
| `ingest_docs.py` | 多格式文档加载 + 切片 |
| `vectorstore_setup.py` | 向量化 + ChromaDB 存储 |
| `rag_chat_bot.py` | 带记忆的 RAG 聊天机器人 |
| `auto_ingest.py` | watchdog 自动文档监听 |
| `config.py` | 配置加载器（YAML + 环境变量） |
| `skill_manager.py` | 闭环学习：问答→Skill |
| `config.yaml` | 外部化配置文件 |
| `skills/` | 自动保存的高质量问答 Skills |

## 常见问题

### Q: Ollama 连接失败
```bash
# 检查 Ollama 是否运行
ollama list
# 如果没运行
ollama serve &
```

### Q: 向量库为空
```bash
# 先确认 data/ 目录有文件
ls data/
# 然后重建
python run_rag.py rebuild
```

### Q: 中文乱码
确保所有 .txt 文件使用 UTF-8 编码。

### Q: qwen2.5:14b 未安装或不适合当前硬件
可以替换为任何本地 Ollama 已安装模型：
```bash
ollama list
# 然后编辑 config.yaml 中的 models.chat
```
