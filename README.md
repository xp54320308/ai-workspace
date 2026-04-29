# AI Workspace

> Personal AI-driven knowledge management system — RAG pipeline, LLM Wiki, vector DB monitoring, and ComfyUI workflows.

## Projects

### 1. RAG Pipeline (`/`)
- **Stack**: ChromaDB + LangChain + Ollama (local LLM)
- **Data**: Contract documents (涪江富金坝船闸工程, ¥779.8M contract)
- **Features**: Semantic search, contract clause analysis,计量变更审查
- **Run**: `python run_rag.py`

### 2. LLM Wiki (`/wiki/`)
- Three-layer architecture: raw → wiki compile → SCHEMA rules
- 11+ pages, bidirectional [[wikilinks]]
- Topics: ComfyUI workflows, RAG architecture, Claude Code patterns, etc.

### 3. Vector DB Monitor (`/monitor/`)
- ChromaDB health monitoring: HNSW index integrity, SQLite metadata, disk space
- Daily cron job → Feishu alert on anomaly

### 4. ComfyUI Workflows
- Wan2.2 I2V + Qwen Image Edit for AI comic drama generation
- RTX 5090 D (23GB) optimized

## Stack

| Component | Technology |
|-----------|------------|
| LLM | Ollama + MiMo API |
| Vector DB | ChromaDB 1.5.8 |
| Agent | OpenClaw + Claude Code + Hermes Agent |
| Embedding | nomic-embed-text (768-dim) |
| GPU | RTX 5090 D v2, 23GB |
| OS | Windows + WSL2 |
