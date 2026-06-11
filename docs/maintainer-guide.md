# Maintainer Guide

This guide records the maintenance expectations for AI Workspace.

## Release checklist

Before publishing a release:

- Confirm `README.md` quick start still works.
- Run `python -m compileall .`.
- Test `python run_rag.py status` with no local data.
- Test `python run_rag.py rebuild` with a small synthetic dataset.
- Review `.gitignore` so private data and generated vector stores stay out of Git.
- Update `ROADMAP.md` and release notes.

## Issue triage

Use labels such as:

- `bug`
- `documentation`
- `enhancement`
- `good first issue`
- `security`
- `question`

Ask reporters for:

- Operating system
- Python version
- Ollama version
- Model names
- Exact command run
- Redacted error output
- Minimal synthetic sample file, when needed

## Pull request review

Check:

- Does the change avoid committing private data?
- Are paths configurable rather than machine-specific?
- Does it keep local-first behavior?
- Does it update documentation?
- Can it be tested without private files?

## Security handling

Keep vulnerability reports private until a fix is available. Prefer small patches with clear reproduction notes and avoid publishing sensitive sample documents.
