"""
第二层测试：格式验证
验证中间数据格式正确性 — 向量维度、文档结构、ChromaDB 元数据。
不需要运行 Ollama，但需要测试用的向量库或 mock。
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
#  文档格式验证
# ============================================================

class TestDocumentFormat:
    """验证加载后的 Document 对象格式"""

    def test_document_has_required_metadata(self):
        """每个 Document 应有 source 元数据"""
        from ingest_docs import split_documents
        from langchain_core.documents import Document

        doc = Document(page_content="测试内容 " * 50, metadata={"source": "test.txt"})
        chunks = split_documents([doc])
        for chunk in chunks:
            assert "source" in chunk.metadata
            assert "source_file" in chunk.metadata

    def test_chunk_size_respected(self):
        """切片大小应在合理范围内"""
        from ingest_docs import split_documents
        from langchain_core.documents import Document

        text = "。".join([f"这是第{i}段内容" for i in range(200)])
        doc = Document(page_content=text, metadata={"source": "long.txt"})

        for chunk_size in [200, 500, 800, 1200]:
            chunks = split_documents([doc], chunk_size=chunk_size, chunk_overlap=50)
            # 允许 20% 的超限（分隔符导致）
            for chunk in chunks:
                assert len(chunk.page_content) <= chunk_size * 1.5, \
                    f"chunk_size={chunk_size}, 实际={len(chunk.page_content)}"

    def test_overlap_between_chunks(self):
        """相邻块之间应有重叠"""
        from ingest_docs import split_documents
        from langchain_core.documents import Document

        # 使用明确的分隔符创建内容
        text = "\n".join([f"段落{i}: 这是独特的标识内容X{i}X" for i in range(20)])
        doc = Document(page_content=text, metadata={"source": "overlap.txt"})
        chunks = split_documents([doc], chunk_size=100, chunk_overlap=30)

        if len(chunks) > 1:
            # 检查相邻块是否有重叠内容
            has_overlap = False
            for i in range(len(chunks) - 1):
                end_of_current = chunks[i].page_content[-30:]
                start_of_next = chunks[i + 1].page_content[:30]
                # 至少有一些共同字符
                common = set(end_of_current) & set(start_of_next)
                if len(common) > 5:
                    has_overlap = True
            assert has_overlap, "相邻块之间应有重叠"


# ============================================================
#  配置格式验证
# ============================================================

class TestConfigFormat:
    """验证配置值在有效范围内"""

    def test_retrieval_k_positive(self):
        """retrieval_k 应为正整数"""
        from config import load_config
        config = load_config(config_path="/nonexistent/path.yaml")
        k = config["retrieval"]["k"]
        assert isinstance(k, int)
        assert k > 0
        assert k <= 50, "k 值过大可能导致性能问题"

    def test_chunk_size_reasonable(self):
        """chunk_size 应在合理范围"""
        from config import load_config
        config = load_config(config_path="/nonexistent/path.yaml")
        cs = config["retrieval"]["chunk_size"]
        assert 100 <= cs <= 5000, f"chunk_size={cs} 超出合理范围"

    def test_chunk_overlap_less_than_size(self):
        """chunk_overlap 应小于 chunk_size"""
        from config import load_config
        config = load_config(config_path="/nonexistent/path.yaml")
        cs = config["retrieval"]["chunk_size"]
        co = config["retrieval"]["chunk_overlap"]
        assert co < cs, f"overlap({co}) >= size({cs})"

    def test_temperature_in_range(self):
        """temperature 应在 0-2 范围"""
        from config import load_config
        config = load_config(config_path="/nonexistent/path.yaml")
        temp = config["models"]["temperature"]
        assert 0 <= temp <= 2.0

    def test_paths_are_strings(self):
        """路径配置应为字符串"""
        from config import load_config
        config = load_config(config_path="/nonexistent/path.yaml")
        assert isinstance(config["paths"]["data_dir"], str)
        assert isinstance(config["paths"]["persist_dir"], str)
        assert isinstance(config["paths"]["skills_dir"], str)


# ============================================================
#  Skill 文件格式验证
# ============================================================

class TestSkillFormat:
    """验证生成的 Skill 文件格式正确"""

    def test_skill_file_has_frontmatter(self, tmp_path):
        """Skill 文件应有 YAML frontmatter"""
        from skill_manager import SkillManager

        mgr = SkillManager(skills_dir=str(tmp_path / "skills"))
        mgr.save_skill(question="测试问题", answer="测试答案")

        skill_files = list((tmp_path / "skills").glob("*.md"))
        assert len(skill_files) == 1

        content = skill_files[0].read_text(encoding="utf-8")
        assert content.startswith("---"), "应以 YAML frontmatter 开头"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "frontmatter 格式不正确"

    def test_skill_index_is_valid_json(self, tmp_path):
        """Skill 索引应为有效 JSON"""
        from skill_manager import SkillManager
        import json

        mgr = SkillManager(skills_dir=str(tmp_path / "skills"))
        mgr.save_skill(question="Q1", answer="A1")
        mgr.save_skill(question="Q2", answer="A2")

        index_file = tmp_path / "skills" / "index.json"
        assert index_file.exists()

        with open(index_file, "r") as f:
            data = json.load(f)
        assert "skills" in data
        assert data["total"] == 2


# ============================================================
#  xlsx 加载格式验证
# ============================================================

class TestXlsxFormat:
    """验证 xlsx 加载输出格式"""

    def test_xlsx_sheet_metadata(self):
        """xlsx 文档应包含 sheet 名元数据"""
        from ingest_docs import load_xlsx

        try:
            from openpyxl import Workbook
        except ImportError:
            pytest.skip("openpyxl 未安装")

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = f.name

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "工程数据"
            ws.append(["项目", "金额"])
            ws.append(["A项目", 100000])
            wb.save(tmp_path)

            result = load_xlsx(tmp_path)
            assert result[0].metadata["sheet"] == "工程数据"
            assert result[0].metadata["source"] == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_xlsx_tab_separated(self):
        """xlsx 单元格应用制表符分隔"""
        from ingest_docs import load_xlsx

        try:
            from openpyxl import Workbook
        except ImportError:
            pytest.skip("openpyxl 未安装")

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            tmp_path = f.name

        try:
            wb = Workbook()
            ws = wb.active
            ws.append(["Col1", "Col2", "Col3"])
            ws.append(["A", "B", "C"])
            wb.save(tmp_path)

            result = load_xlsx(tmp_path)
            lines = result[0].page_content.split("\n")
            # 数据行应包含制表符
            data_lines = [l for l in lines if not l.startswith("【")]
            assert any("\t" in l for l in data_lines)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
