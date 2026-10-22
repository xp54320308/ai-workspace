# Offline workspace tools

Python 3.10+ is required. The workspace_tools package uses only the Python standard library.
Run the commands from the repository root. Reports and searches stay on the local machine;
the tools contain no network client.

## Inventory a workspace

~~~sh
python -m workspace_tools catalog examples --depth 1
python -m workspace_tools catalog /path/to/workspace --depth 2 --exclude scratch --output tmp/catalog.json
~~~

The report groups relative paths at the requested depth and counts bytes, code files,
document files, extensions, and common project markers. It reads file metadata, not contents.
Common dependencies, hidden directories, credentials, database files, symbolic links, and
Windows reparse points are skipped. Directory names can still contain private information.

Exclusions are directory names, case-insensitive, not glob expressions. A file count is not
a count of original contributions. Vendored code and generated files outside the excluded
directories may still appear. Errors are reported, not silently treated as complete coverage.
Avoid writing the report inside the scanned tree if comparing successive counts.

## Extract Word body text

~~~sh
python examples/make_sample_docx.py tmp/demo.docx
python -m workspace_tools extract-docx tmp/demo.docx
python -m workspace_tools extract-docx tmp/demo.docx --format json --output tmp/demo-blocks.json
~~~

The JSON output preserves paragraph/table order, paragraph styles, table rows, and stable
body-block identifiers such as P001 and T001. The text output includes those identifiers.
Chinese text, tabs, explicit line breaks, and content-control wrappers are supported.
Tracked deletions and field instructions are excluded.

The shared extractor is also used by load_docx in the RAG ingestion module, so tables
are no longer silently omitted from that loader.

This is body-text extraction, not rendering. It does not reproduce pagination, numbering,
merged-cell layout, images/OCR, headers, footers, comments, or footnotes. Nested tables are
flattened into their containing cell. DOCX body XML is limited to 32 MiB; DTD/entity
declarations are rejected. Legacy .doc/.wps files must first be converted locally.

## Search without a model service

~~~sh
python -m workspace_tools search examples/knowledge-base "知识库迁移"
python -m workspace_tools search examples/knowledge-base "11434" --limit 3
~~~

Only UTF-8 (optionally BOM-prefixed) .md and .txt files are indexed. Each file is one
document. Files over 2 MiB, binary text, or decoding/read errors are explicitly reported.
Search uses BM25 over English words/numbers and Chinese characters/bigrams, not semantic
embeddings. Chinese segmentation is intentionally lightweight; ranking is heuristic and
scores are not confidence probabilities. Source paths are relative to the input root.

The retrieval design is adapted from the repository's existing BM25 experiment; see
[provenance](provenance.md). This implementation runs independently of LangChain and retains
numbers in queries.

## Check knowledge-base links

~~~sh
python -m workspace_tools check-links .
~~~

Checks conventional inline Markdown file/image links, including angle-bracket targets,
percent-encoded spaces/hash characters, one level of balanced parentheses, and optional
double-quoted titles. Fenced and single-line inline code examples are ignored.
The report gives a source file, line number, target, and reason for each finding.

This is deliberately not a complete CommonMark parser. It does not check reference-style
links, HTML links, anchor existence, remote URLs, or remote availability. It does not rewrite
links or fetch anything. Absolute local paths and targets outside the chosen root are
reported as portability issues. Pick the knowledge-base root, rather than a single subfolder,
if parent-relative links are intentional.

## Exit codes and output

- 0: command completed without reported findings or skipped reads.
- 1: link findings, catalog errors, or skipped search files require review.
- 2: invalid arguments, missing input, malformed DOCX, or output errors.

Search with no matches returns an empty results list and exit code 0. An explicitly supplied
output path is written as UTF-8 and is never overwritten. The DOCX text format is plain text;
other reports and the DOCX JSON format use JSON.

The commands never execute content found in source documents. They do not anonymize arbitrary
documents, detect every secret, or establish publication rights. Use the synthetic examples
when reporting bugs or demonstrating the tools.
