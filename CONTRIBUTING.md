# Contributing to AI Workspace

Thanks for helping improve AI Workspace. This project is early-stage, so clear bug reports, reproducible examples, documentation fixes, and small focused pull requests are especially valuable.

## Good first contributions

- Improve setup docs for Windows, WSL2, Linux, or macOS.
- Add small sample documents that do not contain private or copyrighted data.
- Add tests around config loading, document ingestion, and skill memory.
- Improve error messages for missing Ollama models or vector stores.
- Add examples for common local RAG workflows.

## Development setup

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

Copy local config:

```bash
cp config.example.yaml config.yaml
```

Run a syntax check before submitting:

```bash
python -m compileall .
```

## Pull request guidelines

- Keep changes focused on one behavior or documentation area.
- Do not commit private documents, vector stores, API keys, local paths, or `.env` files.
- Update README or docs when behavior changes.
- Include a short explanation of how you tested the change.
- Prefer configuration over hard-coded machine-specific paths.

## Security issues

Please do not open public issues for suspected vulnerabilities, leaked credentials, or sensitive-data exposure. Follow [SECURITY.md](SECURITY.md).
