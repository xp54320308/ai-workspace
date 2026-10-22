# Changelog

## Unreleased — prepared 2026-10-22

### Added

- Dependency-free CLI tools for workspace catalogs, ordered DOCX body extraction,
  Chinese/English/numeric BM25 search, and local inline Markdown link checks.
- Synthetic knowledge-base notes and a reproducible synthetic DOCX generator.
- Offline regression coverage and a Windows/Linux GitHub Actions test matrix.
- Chinese onboarding, provenance notes, and an inventory of existing experimental branches.
- Persistent removal of obsolete saved skills through SkillManager.delete_skill.

### Fixed

- Repeated configuration loads no longer mutate shared nested defaults.
- Fractional RAG_TEMPERATURE overrides work even when YAML contains an integer zero.
- Non-mapping YAML receives an explicit configuration error.
- The DOCX RAG loader now includes body tables in document order.

### Verification scope

Local offline tests and CLI examples are recorded in the change review. GitHub Actions
results must be checked after publication. Full Ollama/ChromaDB end-to-end behavior and
the entire historical experiment branch were not validated by the offline suite.
