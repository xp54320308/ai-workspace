"""
第三层测试：后端集成测试
调用真实的 Ollama + ChromaDB 验证完整 pipeline。
需要：Ollama 运行中 + nomic-embed-text 模型已下载。

运行: pytest tests/test_backend.py -v -m backend
"""

import os
import sys
import tempfile
import shutil
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 标记所有测试为 backend 级别
pytestmark = pytest.mark.backend


def ollama_available() -> bool:
    """检查 Ollama 是否可用"""
    try:
        import ollama
        client = ollama.Client()
        client.list()
        return True
    except Exception:
        return False


def skip_if_no_ollama():
    """如果 Ollama 不可用则跳过"""
    if not ollama_available():
        pytest.skip("Ollama 未运行")


# ============================================================
#  Embedding 后端测试
# ============================================================

class TestEmbeddingBackend:
    """测试 Ollama Embedding 真实调用"""

    def test_embedding_returns_vector(self):
        """embedding 应返回浮点数列表"""
        skip_if_no_ollama()
        from langchain_ollama import OllamaEmbeddings

        emb = OllamaEmbeddings(model="nomic-embed-text")
        vector = emb.embed_query("测试文本")

        assert isinstance(vector, list)
        assert len(vector) > 0
        assert all(isinstance(v, float) for v in vector)

    def test_embedding_dimension_consistent(self):
        """同一模型的 embedding 维度应一致"""
        skip_if_no_ollama()
        from langchain_ollama import OllamaEmbeddings

        emb = OllamaEmbeddings(model="nomic-embed-text")
        v1 = emb.embed_query("文本一")
        v2 = emb.embed_query("文本二")

        assert len(v1) == len(v2), f"维度不一致: {len(v1)} vs {len(v2)}"

    def test_different_texts_different_vectors(self):
        """不同文本应产生不同向量"""
        skip_if_no_ollama()
        from langchain_ollama import OllamaEmbeddings

        emb = OllamaEmbeddings(model="nomic-embed-text")
        v1 = emb.embed_query("Python 编程语言")
        v2 = emb.embed_query("量子物理原理")

        assert v1 != v2, "不同文本应产生不同向量"


# ============================================================
#  ChromaDB 后端测试
# ============================================================

class TestChromaDBBackend:
    """测试 ChromaDB 真实存储和检索"""

    @pytest.fixture
    def temp_vectordb(self, tmp_path):
        """创建临时向量库"""
        skip_if_no_ollama()
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma
        from langchain_core.documents import Document

        persist_dir = str(tmp_path / "chroma_test")
        emb = OllamaEmbeddings(model="nomic-embed-text")

        docs = [
            Document(page_content="RAG 是检索增强生成技术", metadata={"source": "rag.txt"}),
            Document(page_content="Python 是编程语言", metadata={"source": "python.txt"}),
            Document(page_content="ChromaDB 是向量数据库", metadata={"source": "chroma.txt"}),
        ]

        vs = Chroma.from_documents(docs, emb, persist_directory=persist_dir)
        yield vs
        # cleanup handled by tmp_path

    def test_vectordb_count(self, temp_vectordb):
        """向量库文档数应正确"""
        count = temp_vectordb._collection.count()
        assert count == 3

    def test_similarity_search(self, temp_vectordb):
        """相似度搜索应返回相关文档"""
        results = temp_vectordb.similarity_search("向量存储", k=2)
        assert len(results) <= 2
        # 最相关的应该是 ChromaDB 相关的
        assert any("ChromaDB" in r.page_content or "向量" in r.page_content for r in results)

    def test_search_with_scores(self, temp_vectordb):
        """带分数的搜索应返回 (doc, score) 对"""
        results = temp_vectordb.similarity_search_with_score("RAG 技术", k=2)
        assert len(results) > 0
        for doc, score in results:
            assert hasattr(doc, "page_content")
            assert isinstance(score, float)


# ============================================================
#  完整 Pipeline 测试
# ============================================================

class TestFullPipeline:
    """测试完整的 摄入→切片→向量化→检索 流程"""

    def test_ingest_to_retrieval(self, tmp_path):
        """从文档到检索的完整流程"""
        skip_if_no_ollama()

        # 1. 创建测试文档
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "test.txt").write_text(
            "这是一个关于 RAG 技术的测试文档。\n"
            "RAG 代表检索增强生成 (Retrieval-Augmented Generation)。\n"
            "它通过检索外部知识来增强大语言模型的回答准确性。\n"
            "RAG 系统通常包含三个组件：检索器、生成器和知识库。\n"
            "ChromaDB 是一个常用的本地向量数据库。\n",
            encoding="utf-8",
        )

        # 2. 摄入
        from ingest_docs import load_documents, split_documents
        docs = load_documents(str(data_dir))
        assert len(docs) == 1
        chunks = split_documents(docs, chunk_size=200, chunk_overlap=50)
        assert len(chunks) > 0

        # 3. 向量化
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma

        persist_dir = str(tmp_path / "chroma_db")
        emb = OllamaEmbeddings(model="nomic-embed-text")
        vs = Chroma.from_documents(chunks, emb, persist_directory=persist_dir)

        # 4. 检索
        results = vs.similarity_search("RAG 系统的组件", k=2)
        assert len(results) > 0
        content = " ".join(r.page_content for r in results)
        assert "检索" in content or "RAG" in content

    def test_vectorstore_persistence(self, tmp_path):
        """向量库应能持久化后重新加载"""
        skip_if_no_ollama()
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma
        from langchain_core.documents import Document

        persist_dir = str(tmp_path / "persist_test")
        emb = OllamaEmbeddings(model="nomic-embed-text")

        # 创建并存储
        docs = [Document(page_content="持久化测试内容", metadata={"source": "test.txt"})]
        vs1 = Chroma.from_documents(docs, emb, persist_directory=persist_dir)
        count1 = vs1._collection.count()

        # 重新加载
        vs2 = Chroma(persist_directory=persist_dir, embedding_function=emb)
        count2 = vs2._collection.count()

        assert count1 == count2, "持久化后重新加载，文档数应一致"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "backend"])
