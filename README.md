# AI Workspace

[简体中文](README.zh-CN.md) · [Offline tools](docs/offline-tools.md) · [Existing branches](docs/branches.md) · [Changelog](CHANGELOG.md)

AI Workspace is a local-first knowledge management toolkit for building practical RAG systems, maintaining LLM-oriented project notes, monitoring ChromaDB vector stores, and documenting ComfyUI production workflows.

The repository is early-stage, but it is structured as a reusable open-source workspace for developers who want a transparent local AI stack rather than a hosted black box.

## What is included

| Area | Purpose |
| --- | --- |
| Offline workspace tools | Inventory project metadata, extract DOCX body text/tables, search bilingual notes with BM25, and validate local Markdown links without a model service. |
| RAG pipeline | Load documents, split them into chunks, embed them with Ollama, and store them in ChromaDB. |
| RAG chat | Query the local vector store with a source-aware conversational assistant. |
| Auto ingest | Watch a document folder and rebuild the vector store when supported files change. |
| Skill memory | Save high-value question/answer pairs into a local reusable skill index. |
| LLM wiki | Maintain lightweight linked notes about AI workflows, architecture, and operating patterns. |
| Vector DB monitor | Track vector database health and maintenance notes. |

## Current stack

| Component | Technology |
| --- | --- |
| Language | Python |
| Orchestration | LangChain |
| Vector database | ChromaDB |
| Local inference | Ollama |
| Embeddings | `nomic-embed-text` |
| Default chat model | `qwen2.5:14b` |
| Configuration | YAML + environment variables |
| Target environment | Windows + WSL2, also usable on Linux/macOS with path changes |

## Repository layout

```text
.
|-- auto_ingest.py          # File watcher that rebuilds the vector store
|-- config.example.yaml     # Copy to config.yaml and customize
|-- config.py               # Config loader with environment overrides
|-- ingest_docs.py          # Document loading and chunking
|-- rag_chat_bot.py         # Interactive RAG assistant
|-- run_rag.py              # Main CLI entry point
|-- skill_manager.py        # Local saved Q&A skill index
|-- vectorstore_setup.py    # ChromaDB build pipeline
|-- wiki/                   # Linked notes and operating docs
|-- monitor/                # Vector DB monitoring notes/logs
|-- docs/                   # Project documentation
`-- .github/                # Issue templates and community metadata
```

## Quick start

### Try the offline tools first (no dependencies or model download)

Python 3.10+ is required. These commands use only the standard library:

~~~sh
python -m workspace_tools catalog examples --depth 1
python -m workspace_tools search examples/knowledge-base "11434"
python -m workspace_tools check-links .
python examples/make_sample_docx.py tmp/demo.docx
python -m workspace_tools extract-docx tmp/demo.docx --format json
~~~

See [offline tool behavior and limits](docs/offline-tools.md) and
[where the reusable code comes from](docs/provenance.md).

### Set up the full RAG pipeline

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start Ollama and install models

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:14b
```

Then either update `config.yaml` or set:

```bash
export RAG_CHAT_MODEL=qwen2.5:14b
```

### 3. Create local config

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` and set:

- `paths.data_dir` to the folder containing your source documents
- `paths.persist_dir` to the folder where ChromaDB should store its index
- `models.chat` to a model available in your local Ollama installation

### 4. Add documents

Create a `data/` directory and add supported files:

```text
.txt, .md, .pdf, .docx, .xlsx
```

Do not commit private documents. The included `.gitignore` excludes `data/`, `config.yaml`, local vector stores, and generated skill indexes.

### 5. Build and query

```bash
python run_rag.py rebuild
python run_rag.py query "What does this knowledge base contain?"
python run_rag.py chat
```

## CLI commands

| Command | Description |
| --- | --- |
| `python run_rag.py ingest` | Load and chunk documents without writing vectors. |
| `python run_rag.py build` | Build or update the ChromaDB vector store. |
| `python run_rag.py rebuild` | Clear the old vector store and rebuild from scratch. |
| `python run_rag.py chat` | Start the interactive RAG assistant. |
| `python run_rag.py query "..."` | Run one non-interactive query. |
| `python run_rag.py status` | Show document, vector store, and skill-memory status. |
| `python run_rag.py auto` | Watch the data directory and rebuild on file changes. |
| `python run_rag.py skills` | List locally saved skills. |
| `python run_rag.py skill-stats` | Show saved-skill statistics. |

## Environment variables

These variables override values in `config.yaml`:

| Variable | Config path |
| --- | --- |
| `RAG_DATA_DIR` | `paths.data_dir` |
| `RAG_PERSIST_DIR` | `paths.persist_dir` |
| `RAG_EMBEDDING_MODEL` | `models.embedding` |
| `RAG_CHAT_MODEL` | `models.chat` |
| `RAG_TEMPERATURE` | `models.temperature` |
| `RAG_RETRIEVAL_K` | `retrieval.k` |
| `RAG_CHUNK_SIZE` | `retrieval.chunk_size` |
| `RAG_CHUNK_OVERLAP` | `retrieval.chunk_overlap` |
| `RAG_MAX_HISTORY` | `chat.max_history` |
| `OLLAMA_BASE_URL` | `ollama.base_url` |

## Security and privacy

AI Workspace is designed for local knowledge work. It may process sensitive documents, local vector stores, and configuration files, so the default repository hygiene is conservative:

- Keep private documents in `data/` and do not commit that folder.
- Keep machine-specific settings in `config.yaml`, not `config.example.yaml`.
- Keep generated ChromaDB files outside the repository or in ignored local folders.
- Review `SECURITY.md` before reporting vulnerabilities or handling sensitive examples.

## Documentation

- [Getting started](docs/getting-started.md)
- [Offline workspace tools](docs/offline-tools.md)
- [Provenance and scope](docs/provenance.md)
- [Existing experimental branches](docs/branches.md)
- [Maintainer guide](docs/maintainer-guide.md)
- [Roadmap](ROADMAP.md)
- [Security policy](SECURITY.md)

## Project status

This project is early-stage. The offline utilities have synthetic regression tests and a
GitHub Actions workflow; full model/vector-store integration still requires a separate
environment. Advanced retrieval and indexing experiments already exist in other
[branches](docs/branches.md). Next priorities are dependency compatibility, broader RAG
integration coverage, and release automation.

Run the offline regression suite with:

~~~sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
~~~

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening issues or pull requests.

## License

MIT License. See [LICENSE](LICENSE).
