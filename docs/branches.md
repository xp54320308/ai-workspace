# Repository branches and integration status

Inspected on 2026-10-22. Commit IDs below record the branch heads seen at that time;
branch names can move.

| Branch | Inspected head | Contents | Verification status |
| --- | --- | --- | --- |
| main | dedb7e2 | RAG CLI, multi-format ingestion, JSON skill memory, wiki, project documentation | Baseline before the offline-toolset change |
| rag-optimization | 432edbf | BM25/hybrid retrieval, reranking/query expansion, caches, incremental indexing, metadata enrichment, evaluation scripts and tests | Existing experimental code; full branch not rerun in this maintenance pass |
| master | c4034b2 | OpenClaw-oriented assistant workspace, skills, automation scripts and workflows | Separate workspace snapshot; not merged into the RAG mainline |

The advanced RAG work includes the earlier implementation commit
[f5364e2](https://github.com/xp54320308/ai-workspace/commit/f5364e2).
These capabilities should not be described as absent merely because the default branch
does not expose them. Conversely, their documentation should not be read as proof that
every integration is working against current dependency versions.

## Current integration

The offline tools and core fixes are proposed as a focused mainline extension. BM25 search
has been adapted to run without a model service or LangChain. Existing application-specific
files and datasets are not imported wholesale.

Before integrating another experimental module:

1. Identify its public API, dependencies, license/source, and configuration requirements.
2. Replace machine-specific paths and private fixtures with configurable paths and synthetic data.
3. Add regression tests that demonstrate the actual behavior.
4. Validate the selected module against the mainline; rerun backend tests separately when needed.
5. Document remaining gaps rather than copying a claim of production readiness.

See [provenance](provenance.md) for the distinction between local experiments,
reusable source, and published upstream contributions.
