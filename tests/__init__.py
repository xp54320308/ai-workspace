"""
RAG 项目测试套件 — 四层测试架构

第一层 test_core.py    — 单元测试（合成数据，无外部依赖）
第二层 test_format.py  — 格式验证（数据结构正确性）
第三层 test_backend.py — 后端测试（真实 Ollama + ChromaDB）
第四层 test_e2e.py     — 端到端（CLI 子进程 + 完整流程）

用法:
  pytest tests/ -v                     # 运行所有测试
  pytest tests/ -v -m "not backend"   # 跳过后端测试
  pytest tests/ -v -m core            # 只运行单元测试
  pytest tests/ -v -m backend         # 只运行后端测试
  pytest tests/ -v -m e2e             # 只运行端到端测试
"""

# pytest markers
markers = [
    "core: 单元测试（无需外部依赖）",
    "backend: 后端集成测试（需要 Ollama）",
    "e2e: 端到端测试（需要完整环境）",
]
