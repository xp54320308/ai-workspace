# Provenance and scope

This project contains work developed with coding assistants. Reusable code is maintained
under the repository's [MIT license](../LICENSE). Project documents, personal conversations,
and bundled upstream dependencies are not being relicensed as original software.

## Where the new utilities come from

| Capability | Earlier work examined | What is included here |
| --- | --- | --- |
| DOCX body extraction | Paragraph/table review scripts, including extract_docx_blocks.py | A parameterized standard-library implementation, with body order, styles, deleted-text handling, and synthetic fixtures |
| Local text search | Knowledge handover lookup scripts and the existing BM25 experiment | A dependency-free BM25 index and CLI with Chinese/English/numeric queries |
| Workspace catalog | Local project and artifact inventories | Relative-path metadata summaries, explicit exclusions, and no directory-link traversal |
| Link validation | Knowledge-base migration/index-link repair work, including fix_index_links.py | An offline checker with file/line findings; no automatic rewriting |
| Core regressions | Existing YAML configuration and JSON skill-memory implementation | Configuration isolation/fractional-temperature fixes, persistent skill removal, and tests |

The older scripts were inspected as local working artifacts. They are not asserted to be
public upstream contributions. The generalized implementations and tests in this change
were prepared on 2026-10-22; that date must not be backdated into historical project work.

The search experiment can be inspected at
[the existing BM25 source](https://github.com/xp54320308/ai-workspace/blob/f5364e2/bm25_retriever.py).
The new implementation retains the BM25 approach while removing the LangChain dependency
for offline use and changing tokenization to retain numbers and overlapping Chinese bigrams.

## Material deliberately left out

The following are not part of the reusable source package: operational records, contracts,
internal procedures, medical or account information, transcripts, credentials, browser profiles,
third-party installer payloads, proprietary/minified web bundles, and vendor dependency trees.

Application audit and Windows deployment work also exists among the local artifacts. It
informs future documentation and test practices, but this change does not claim that those
entire applications have been published or fully tested as part of AI Workspace.

## Evidence boundaries

Existing [experimental branches](branches.md) are separate from the mainline offline toolset.
Their presence is evidence that code exists, not proof of release readiness, production
adoption, author identity for every line, or successful end-to-end testing.

Synthetic examples are authored for this repository and contain no copied business data.
Local inventory reports should stay local unless their paths and metadata are reviewed.
