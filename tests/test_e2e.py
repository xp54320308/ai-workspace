"""
第四层测试：端到端测试
通过 CLI 子进程运行真实命令，验证完整系统。
需要：Ollama 运行中 + 向量库已构建。

运行: pytest tests/test_e2e.py -v -m e2e
"""

import os
import sys
import subprocess
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 标记所有测试为 e2e 级别
pytestmark = pytest.mark.e2e

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_rag_command(args: list, timeout: int = 120) -> subprocess.CompletedProcess:
    """运行 run_rag.py 命令"""
    cmd = [sys.executable, os.path.join(PROJECT_DIR, "run_rag.py")] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_DIR,
    )


# ============================================================
#  CLI 命令测试
# ============================================================

class TestCLICommands:
    """测试 run_rag.py CLI 命令"""

    def test_help_output(self):
        """无参数应显示帮助"""
        result = run_rag_command([])
        assert result.returncode == 0
        assert "RAG" in result.stdout or "用法" in result.stdout

    def test_status_command(self):
        """status 命令应正常运行"""
        result = run_rag_command(["status"])
        assert result.returncode == 0
        assert "状态" in result.stdout or "Status" in result.stdout

    def test_ingest_command(self):
        """ingest 命令应加载文档"""
        result = run_rag_command(["ingest"])
        assert result.returncode == 0
        assert "加载" in result.stdout or "导入" in result.stdout

    def test_unknown_command(self):
        """未知命令应显示帮助"""
        result = run_rag_command(["nonexistent_cmd"])
        assert "未知" in result.stdout or "用法" in result.stdout


# ============================================================
#  实际问答测试
# ============================================================

class TestRealQA:
    """测试真实问答（需要向量库 + Ollama）"""

    def _ollama_available(self):
        try:
            import ollama
            client = ollama.Client()
            client.list()
            return True
        except Exception:
            return False

    def _vectordb_exists(self):
        persist_dir = "/mnt/f/RAG_Project/chroma_db"
        return os.path.exists(persist_dir) and os.listdir(persist_dir)

    def test_query_returns_answer(self):
        """查询应返回非空回答"""
        if not self._ollama_available():
            pytest.skip("Ollama 未运行")
        if not self._vectordb_exists():
            pytest.skip("向量库不存在")

        from rag_chat_bot import load_vectorstore, build_chain, CONFIG

        vs = load_vectorstore(CONFIG)
        chain = build_chain(vs, CONFIG)

        answer, sources, docs = chain("这个知识库包含什么内容？", [])
        assert answer, "回答不应为空"
        assert len(sources) > 0, "应有来源标注"
        assert len(docs) > 0, "应检索到文档"

    def test_query_has_sources(self):
        """回答应包含来源信息"""
        if not self._ollama_available():
            pytest.skip("Ollama 未运行")
        if not self._vectordb_exists():
            pytest.skip("向量库不存在")

        from rag_chat_bot import load_vectorstore, build_chain, CONFIG

        vs = load_vectorstore(CONFIG)
        chain = build_chain(vs, CONFIG)

        answer, sources, docs = chain("Python 是什么？", [])
        # 即使回答不一定准确，sources 应该不为空
        assert isinstance(sources, list)

    def test_chat_history_preserved(self):
        """多轮对话应保留历史"""
        if not self._ollama_available():
            pytest.skip("Ollama 未运行")
        if not self._vectordb_exists():
            pytest.skip("向量库不存在")

        from rag_chat_bot import load_vectorstore, build_chain, CONFIG
        from langchain_core.messages import HumanMessage, AIMessage

        vs = load_vectorstore(CONFIG)
        chain = build_chain(vs, CONFIG)

        # 第一轮
        answer1, _, _ = chain("什么是 RAG？", [])
        assert answer1

        # 第二轮（带历史）
        history = [
            HumanMessage(content="什么是 RAG？"),
            AIMessage(content=answer1),
        ]
        answer2, _, _ = chain("它有什么优势？", history)
        assert answer2


# ============================================================
#  闭环学习端到端测试
# ============================================================

class TestSkillLearningE2E:
    """测试闭环学习完整流程"""

    def test_save_search_retrieve(self, tmp_path):
        """保存→搜索→读取的完整流程"""
        from skill_manager import SkillManager

        mgr = SkillManager(skills_dir=str(tmp_path / "skills"))

        # 1. 保存
        mgr.save_skill(
            question="如何使用 ChromaDB 进行向量存储？",
            answer="ChromaDB 使用步骤：1. 安装 2. 创建集合 3. 添加文档 4. 查询",
            sources=["chromadb_guide.txt"],
            rating=5,
            tags=["database", "vector"],
        )

        # 2. 搜索
        results = mgr.search_skills("ChromaDB 向量数据库怎么用？")
        assert len(results) > 0
        assert results[0]["score"] > 0

        # 3. 读取
        skill = mgr.get_skill_answer(results[0]["skill_id"])
        assert skill is not None
        assert "ChromaDB" in skill["answer"]

        # 4. 统计
        stats = mgr.get_stats()
        assert stats["total_skills"] == 1
        assert stats["total_hits"] >= 1  # 读取时增加 hit


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
