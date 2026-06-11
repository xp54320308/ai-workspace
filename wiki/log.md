# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> When this file exceeds 500 entries, rotate: rename to log-YYYY.md, start fresh.

## [2026-04-18] create | Wiki initialized
- Domain: 个人AI工程综合知识库（RAG/ComfyUI/Agent/Ollama/工程管理）
- Structure created with SCHEMA.md, index.md, log.md
- Three-layer architecture: raw/ (immutable sources), wiki pages (entities/concepts/comparisons/queries), SCHEMA.md (rules)

## [2026-04-18] ingest | 初始知识库构建
- Raw sources created: rag-project-overview.md, comfyui-comic-workflow.md, hermes-agent-overview.md
- Wiki pages created (8 total):
  - Entities: rag-project-v3, ollama, comfyui-comic-workflow, rtx-5090-d-v2, hermes-agent
  - Concepts: chroma-vector-store, llm-wiki-skill
  - Comparisons: rag-vs-llm-wiki
- Cross-references established between all pages via [[wikilinks]]
- index.md updated with all 8 pages

## [2026-04-18] lint | Wiki 健康检查
- Total pages: 8 → 11 (修复断链后)
- Found 4 broken wikilinks: wan2-video-models, comfyui-秋叶包, langchain (x2)
- Fixed: created 3 new pages to resolve all broken links
- Orphan pages: 0
- Pages missing from index: 0
- All pages have valid frontmatter

## [2026-04-18] update | 修复断链 + 补充页面
- New pages created: wan2-video-models, comfyui-秋叶包, langchain
- All broken wikilinks resolved
- index.md updated to 11 pages

## [2026-04-22] ingest | Karpathy LLM Coding Guidelines
- Source: forrestchang/andrej-karpathy-skills (73.9k stars, MIT)
- New page: concepts/karpathy-llm-coding-guidelines.md
- 4 core principles: Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution
- Updated: index.md (11→12 pages), log.md

## [2026-04-25] update | 补充LLM Wiki文章内容
- Source: 微信公众号技术文章《LLM Wiki（编译型知识库）》
- 新增raw来源: raw/articles/llm-wiki-article.md
- 更新 comparisons/rag-vs-llm-wiki.md：
  - 补充"金鱼问题"解释（每次查询重复读原文）
  - 补充Token消耗对比表（96%节省）
  - 补充LLM Wiki 4步编译流程
  - 补充"书童递小抄"比喻
- 更新 index.md sources 引用

## [2026-04-26] ingest | Camofox 浏览器自动化服务
- npm包: @askjo/camofox-browser v1.7.2
- 新增entities: camofox.md, camoufox-js.md
- 配置: CAMOFOX_URL=http://localhost:9377 (写入~/.hermes/.env)
- config.yaml: browser.camofox.managed_persistence=false
- 坑点记录: 包名历史混淆(jo-inc→@askjo), 无PATH命令, fetch超时属正常
- index.md更新: 12→14 pages

## [2026-04-26] update | Camofox 开机自启 + 端口隐藏
- systemd user service: ~/.config/systemd/user/camofox.service
- 绑定127.0.0.1 (server.js:5020)，外部无法访问
- 服务已enable，开机自动启动
- wiki更新: camofox.md补充自启配置和端口隐藏说明
