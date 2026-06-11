# Wiki Schema

## Domain
个人AI工程综合知识库 — 覆盖本地大模型部署（Ollama）、RAG检索增强生成（LangChain + ChromaDB）、ComfyUI视频生成工作流、AI Agent开发（Hermes Agent）、以及工程管理应用。

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `chroma-vector-store.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`

## Frontmatter
  ```yaml
  ---
  title: Page Title
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  type: entity | concept | comparison | query | summary
  tags: [from taxonomy below]
  sources: [raw/articles/source-name.md]
  ---
  ```

## Tag Taxonomy

### 模型与推理
- `ollama` `llm` `inference` `quantization` `gguf` `vision` `embedding`

### RAG系统
- `rag` `langchain` `chromadb` `vector-store` `retrieval` `chunking` `embedding-model`

### ComfyUI与视频生成
- `comfyui` `wan2` `qwen` `i2v` `video-generation` `漫剧` `workflow` `first-last-frame`

### Agent与工具
- `agent` `hermes` `skill` `tool` `multi-agent` `mcp` `self-evolution`

### 开发与环境
- `wsl` `powershell` `python` `node` `docker` `gpu` `rtx5090`

### 工程管理
- `contract` `construction` `ship-lock` `project-management` `fujinba`

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, minor details, or things outside the domain
- **Split a page** when it exceeds ~200 lines — break into sub-topics with cross-links
- **Archive a page** when its content is fully superseded — move to `_archive/`, remove from index

## Entity Pages
One page per notable entity. Include:
- Overview / what it is
- Key facts and dates
- Relationships to other entities ([[wikilinks]])
- Source references

## Concept Pages
One page per concept or topic. Include:
- Definition / explanation
- Current state of knowledge
- Open questions or debates
- Related concepts ([[wikilinks]])

## Comparison Pages
Side-by-side analyses. Include:
- What is being compared and why
- Dimensions of comparison (table format preferred)
- Verdict or synthesis
- Sources

## Update Policy
When new information conflicts with existing content:
1. Check the dates — newer sources generally supersede older ones
2. If genuinely contradictory, note both positions with dates and sources
3. Mark the contradiction in frontmatter: `contradictions: [page-name]`
4. Flag for user review in the lint report
