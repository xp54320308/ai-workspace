# Getting Started

This guide walks through a minimal local setup for AI Workspace.

## Prerequisites

- Python 3.10 or newer
- Ollama installed and running
- Enough disk space for local vector stores and model files

Install Ollama models:

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:14b
```

## Install

```bash
git clone https://github.com/xp54320308/ai-workspace.git
cd ai-workspace
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

On Windows PowerShell:

```powershell
git clone https://github.com/xp54320308/ai-workspace.git
cd ai-workspace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item config.example.yaml config.yaml
```

## Configure paths

Edit `config.yaml`:

```yaml
paths:
  data_dir: "data"
  persist_dir: "chroma_db"
  skills_dir: "skills"

models:
  embedding: "nomic-embed-text"
  chat: "qwen2.5:14b"
```

The repository ignores `data/`, `chroma_db/`, and `skills/` so local knowledge files and generated state are not committed accidentally.

## Add documents

Create `data/` and add supported files:

```bash
mkdir data
```

Supported formats:

- `.txt`
- `.md`
- `.pdf`
- `.docx`
- `.xlsx`

Use synthetic or public sample documents when sharing bug reports.

## Build the vector store

```bash
python run_rag.py rebuild
```

## Ask a question

```bash
python run_rag.py query "Summarize this knowledge base."
```

For an interactive session:

```bash
python run_rag.py chat
```

## Watch for document changes

```bash
python run_rag.py auto
```

The watcher rebuilds the vector store after supported files are added, changed, moved, or deleted.
