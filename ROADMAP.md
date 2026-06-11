# Roadmap

This roadmap describes the near-term direction for AI Workspace. It is intentionally practical: the goal is to make local RAG systems easier to reproduce, inspect, and maintain.

## Now

- Stabilize setup instructions for Windows, WSL2, Linux, and macOS.
- Add repository hygiene: license, contribution guide, security policy, and issue templates.
- Keep local data, vector stores, and generated skill memory out of Git by default.
- Document the main CLI workflows.

## Next

- Add automated tests for configuration loading, document ingestion, and skill memory.
- Add GitHub Actions for linting and syntax checks.
- Add a small synthetic sample dataset for demos.
- Improve error messages when Ollama is missing or models are not installed.
- Move hard-coded paths in watcher utilities fully behind config.

## Later

- Add a lightweight UI for local RAG status and query testing.
- Add vector database health checks for HNSW/index integrity and disk usage.
- Add release automation and versioned changelogs.
- Add optional OCR workflows for scanned PDFs.
- Add templates for project-specific RAG workspaces.

## Open questions

- Which embedding models should be recommended for Chinese and bilingual documents?
- What is the best default chunking strategy for contracts, technical notes, and workflow docs?
- Should skill memory stay JSON-based or move into a small SQLite database?
- How much monitoring belongs in the core project versus optional plugins?
