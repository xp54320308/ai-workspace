# 📦 RAG Pipeline — 安装指南（Tier 0/1/2）

## 系统要求

| 最低要求 | 推荐配置 |
|----------|----------|
| Python 3.10+ | Python 3.11+ |
| 8GB RAM | 16GB+ RAM |
| Ollama 已安装 | Ollama + gemma4:26b |
| 2GB 磁盘空间 | 10GB+ (含模型和向量库) |

---

## Tier 0：零配置（5分钟启动）

> **适合：** 快速体验、个人使用、纯文本/Markdown 知识库

### 步骤 1：确认 Ollama 运行

```bash
ollama list
# 应该看到至少 nomic-embed-text 和一个 chat 模型
```

如果没有：
```bash
ollama pull nomic-embed-text
ollama pull gemma4:26b    # 或 qwen2.5:14b 作为稳定备选
```

### 步骤 2：激活虚拟环境

```bash
cd /mnt/c/Users/qw/Documents/RAG_Project
source venv/bin/activate
```

### 步骤 3：安装核心依赖

```bash
pip install -r requirements.txt
```

**核心依赖清单：**
```
langchain>=0.3.0
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-ollama>=0.2.0
langchain-chroma>=0.2.0
langchain-text-splitters>=0.3.0
pypdf>=4.0.0
python-docx>=1.0.0
chromadb>=0.5.0
ollama>=0.4.0
```

### 步骤 4：构建并启动

```bash
python run_rag.py rebuild   # 全量构建向量库
python run_rag.py chat      # 启动聊天
```

✅ **完成！** 支持 `.txt`, `.pdf`, `.md`, `.docx` 格式。

---

## Tier 1：多格式增强（+10分钟）

> **适合：** 需要处理 Excel、扫描 PDF 的专业场景

### 在 Tier 0 基础上，额外安装：

#### Excel 支持（.xlsx）

```bash
pip install openpyxl>=3.1.0
```

#### 扫描 PDF 支持（PaddleOCR）

```bash
# CPU 版本（轻量）
pip install paddlepaddle paddleocr

# GPU 版本（需 CUDA，你的 RTX 5090 可用）
pip install paddlepaddle-gpu paddleocr
```

#### 自动文档监听（watchdog）

```bash
pip install watchdog>=3.0.0
```

安装后：
```bash
python run_rag.py auto   # 自动监听 data/ 目录变化
```

### 更新 requirements.txt

```bash
cat >> requirements.txt << 'EOF'

# Tier 1：多格式增强
openpyxl>=3.1.0
watchdog>=3.0.0
EOF
```

✅ **完成！** 额外支持 `.xlsx`、扫描 PDF、自动监听。

---

## Tier 2：高级配置

> **适合：** 生产部署、自定义模型、性能调优

### 步骤 1：创建配置文件

```bash
# 复制示例配置
cp config.example.yaml config.yaml
```

### 步骤 2：编辑 config.yaml

```yaml
# 路径配置
paths:
  data_dir: "data"
  persist_dir: "/mnt/f/RAG_Project/chroma_db"
  skills_dir: "skills"

# 模型配置
models:
  embedding: "nomic-embed-text"
  chat: "gemma4:26b"
  temperature: 0

# 检索配置
retrieval:
  k: 5                    # 检索文档块数
  score_threshold: 0.0    # 相似度阈值（0=不过滤）
  chunk_size: 800         # 文本块大小
  chunk_overlap: 100      # 块间重叠

# 对话配置
chat:
  max_history: 10         # 记忆轮数
  system_prompt: ""       # 自定义系统提示（留空使用默认）

# 自动监听
auto_ingest:
  enabled: true
  debounce_seconds: 3
  supported_extensions: [".txt", ".pdf", ".md", ".docx", ".xlsx"]

# 闭环学习
skill_learning:
  enabled: true
  min_rating: 4           # 最低评分才保存为 Skill（1-5）
  auto_save: false        # 是否自动保存高质量问答

# Ollama 配置
ollama:
  base_url: "http://localhost:11434"
  timeout: 120
```

### 步骤 3：GPU 优化（RTX 5090）

```bash
# 确认 CUDA 可用
python -c "import torch; print(torch.cuda.is_available())"

# 如果使用 Ollama GPU 模式
ollama run gemma4:26b --gpu
```

### 步骤 4：自定义系统提示

编辑 `config.yaml` 中的 `chat.system_prompt` 字段，或创建 `prompts/custom_system.txt`。

### 步骤 5：性能调优

| 参数 | 低配（8GB） | 中配（16GB） | 高配（128GB + RTX 5090） |
|------|------------|-------------|------------------------|
| chunk_size | 500 | 800 | 1200 |
| chunk_overlap | 50 | 100 | 200 |
| retrieval_k | 3 | 5 | 10 |
| max_history | 5 | 10 | 20 |
| chat_model | qwen2.5:7b | gemma4:26b | gemma4:26b |

✅ **完成！** 全功能配置，可按需定制。

---

## 故障排查

### 环境检查清单

```bash
# 1. Python 版本
python --version   # 需要 3.10+

# 2. Ollama 状态
ollama list        # 应列出模型

# 3. 依赖检查
pip list | grep -E "langchain|chroma|ollama"

# 4. 向量库状态
python run_rag.py status

# 5. 管道测试
python run_rag.py test
```

### 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: langchain_text_splitters` | 依赖未安装 | `pip install langchain-text-splitters` |
| `ConnectionRefusedError` | Ollama 未运行 | `ollama serve &` |
| `chromadb...no such table` | 向量库损坏 | `python run_rag.py rebuild` |
| `chmod error` on /mnt/f/ | WSL 权限问题 | 使用 Windows 原生 Python |
| `gemma4:26b crash` | 模型不稳定 | 换用 `qwen2.5:14b` |
