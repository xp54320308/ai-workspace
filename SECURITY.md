# Security Policy

AI Workspace handles local documents, vector database files, model prompts, and configuration. Treat all real-world knowledge bases as potentially sensitive.

## Supported versions

This project is in active early development. Security fixes are applied to the `main` branch until formal releases are created.

## Reporting a vulnerability

Please do not report security issues in public GitHub issues.

If you find a vulnerability, create a private security advisory on GitHub if available, or contact the maintainer through the GitHub profile associated with this repository. Include:

- Affected file or workflow
- Reproduction steps
- Impact
- Any relevant logs with secrets removed
- Suggested fix, if known

## Sensitive data guidelines

- Do not commit source documents from private projects.
- Do not commit generated ChromaDB indexes.
- Do not commit API keys, OpenAI organization IDs tied to private accounts, `.env` files, or local credentials.
- Redact names, contracts, phone numbers, email addresses, and proprietary text in examples.
- Prefer synthetic sample documents for issues and tests.

## Areas of interest

Security review is especially welcome for:

- Unsafe file handling in document ingestion
- Path traversal or accidental indexing outside the intended data directory
- Secret leakage in logs, examples, or generated skills
- Dependency vulnerabilities
- Prompt/data exposure in RAG outputs
- Insecure defaults in watcher or automation workflows
