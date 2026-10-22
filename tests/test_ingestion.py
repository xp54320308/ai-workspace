"""Exercise the real RAG DOCX loader with synthetic OOXML and LangChain Documents."""

import tempfile
import unittest
from pathlib import Path

from examples.make_sample_docx import create_sample
from ingest_docs import load_docx


class DocxIngestionTests(unittest.TestCase):
    def test_table_content_is_preserved_in_langchain_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.docx"
            create_sample(path)
            documents = load_docx(str(path))
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].metadata["source"], str(path))
            text = documents[0].page_content
            self.assertIn("知识库迁移", text)
            self.assertLess(text.index("Demo knowledge"), text.index("知识库迁移"))
            self.assertLess(text.index("知识库迁移"), text.index("follows the table"))


if __name__ == "__main__":
    unittest.main()
