"""Regression tests with synthetic inputs; no network, model service, or private files."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from examples.make_sample_docx import BODY, create_sample
from workspace_tools.__main__ import main
from workspace_tools.catalog import build_catalog
from workspace_tools.docx import extract_docx, render_blocks
from workspace_tools.links import check_links
from workspace_tools.search import BM25Index, SearchDocument, load_text_documents


class TemporaryWorkspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, path, text=""):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def xml_docx(self, xml):
        target = self.root / "fixture.docx"
        with ZipFile(target, "w") as archive:
            archive.writestr("word/document.xml", xml)
        return target


class CatalogTests(TemporaryWorkspace):
    def test_groups_projects_and_skips_dependencies_and_credentials(self):
        self.write("2026-01-01/demo/main.py", "print('example')")
        self.write("2026-01-01/demo/README.md", "# Demo")
        for path in ("node_modules/lib/index.js", ".deps/lib.py", ".hidden/file.txt",
                     "auth.json", "config.yaml", ".env.local", "local.sqlite3"):
            self.write(path, "must not be included")
        result = build_catalog(self.root)
        self.assertEqual(result["totals"]["files"], 2)
        self.assertEqual(result["totals"]["code_files"], 1)
        self.assertEqual(result["projects"][0]["path"], "2026-01-01/demo")
        self.assertFalse(result["errors"])
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_custom_exclusions_and_depth(self):
        self.write("day/project/src/main.py")
        self.write("day/project/scratch/temp.py")
        result = build_catalog(self.root, depth=1, exclude=["scratch"])
        self.assertEqual(result["totals"]["files"], 1)
        self.assertEqual(result["projects"][0]["path"], "day")

    def test_links_are_not_followed(self):
        self.write("source.txt", "one")
        try:
            (self.root / "alias.txt").symlink_to(self.root / "source.txt")
            (self.root / "alias-dir").symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symlinks is unavailable")
        self.assertEqual(build_catalog(self.root)["totals"]["files"], 1)

    def test_invalid_root_or_depth(self):
        with self.assertRaises(FileNotFoundError):
            build_catalog(self.root / "missing")
        with self.assertRaises(ValueError):
            build_catalog(self.root, depth=0)
        with self.assertRaises(ValueError):
            build_catalog(self.write("file.txt"))


class DocxTests(TemporaryWorkspace):
    def test_paragraph_table_order_and_chinese_cells(self):
        target = self.root / "sample.docx"
        create_sample(target)
        blocks = extract_docx(target)
        self.assertEqual([b["kind"] for b in blocks], ["paragraph", "table", "paragraph"])
        self.assertEqual(blocks[0]["style"], "Heading1")
        self.assertEqual(blocks[1]["rows"][1][0], "知识库迁移")
        self.assertEqual(blocks[-1]["id"], "P002")
        rendered = render_blocks(blocks)
        self.assertLess(rendered.index("知识库迁移"), rendered.index("follows the table"))

    def test_deleted_text_and_field_instructions_are_excluded(self):
        xml = BODY.replace(
            "<w:sectPr/>",
            '<w:p><w:del><w:r><w:delText>Old secret</w:delText></w:r></w:del>'
            '<w:r><w:instrText>hidden instruction</w:instrText><w:t>Accepted</w:t></w:r></w:p>'
        )
        text = render_blocks(extract_docx(self.xml_docx(xml)))
        self.assertIn("Accepted", text)
        self.assertNotIn("Old secret", text)
        self.assertNotIn("hidden instruction", text)

    def test_content_controls_are_unwrapped(self):
        xml = BODY.replace(
            "<w:sectPr/>",
            "<w:sdt><w:sdtContent><w:p><w:r><w:t>Wrapped</w:t></w:r></w:p>"
            "</w:sdtContent></w:sdt>"
        )
        self.assertIn("Wrapped", render_blocks(extract_docx(self.xml_docx(xml))))

    def test_broken_zip_missing_body_and_malformed_xml(self):
        with self.assertRaisesRegex(ValueError, "Expected a DOCX"):
            extract_docx(self.write("plain.docx", "not a zip"))
        with self.assertRaisesRegex(ValueError, "missing"):
            extract_docx(self.xml_docx(
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
            ))
        with self.assertRaisesRegex(ValueError, "Invalid"):
            extract_docx(self.xml_docx("<invalid"))

    def test_xml_size_limit(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            extract_docx(self.xml_docx(BODY), max_xml_bytes=16)

    def test_entity_declarations_rejected(self):
        xml = BODY.replace(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<!DOCTYPE document [<!ENTITY example "expanded">]>'
        )
        for encoded in (xml.encode("utf-8"), xml.encode("utf-16")):
            with self.assertRaisesRegex(ValueError, "DTD"):
                extract_docx(self.xml_docx(encoded))

    def test_tabs_breaks_and_empty_document(self):
        xml = BODY.replace(
            "This paragraph follows the table.",
            "First</w:t><w:tab/><w:t>Second</w:t><w:br/><w:t>Third"
        )
        self.assertIn("First\tSecond\nThird", render_blocks(extract_docx(self.xml_docx(xml))))
        empty = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>'
        self.assertEqual(extract_docx(self.xml_docx(empty)), [])


class SearchTests(TemporaryWorkspace):
    def setUp(self):
        super().setUp()
        self.docs = [
            SearchDocument("migration.md", "知识库迁移完成后检查相对链接"),
            SearchDocument("models.md", "Ollama server listens on port 11434"),
            SearchDocument("empty.md", ""),
        ]

    def test_chinese_query_and_numeric_model_terms(self):
        index = BM25Index(self.docs)
        self.assertEqual(index.search("知识库迁移")[0]["source"], "migration.md")
        self.assertEqual(index.search("11434")[0]["source"], "models.md")
        self.assertEqual(index.search("OLLAMA")[0]["source"], "models.md")

    def test_no_irrelevant_or_zero_score_results(self):
        index = BM25Index(self.docs)
        self.assertEqual(index.search("totallyunrelated"), [])
        self.assertEqual(index.search(""), [])
        self.assertEqual(BM25Index([]).search("query"), [])
        self.assertEqual(len(index.search("port", limit=1)), 1)

    def test_repeated_query_does_not_duplicate_scores(self):
        index = BM25Index(self.docs)
        self.assertEqual(index.search("Ollama"), index.search("Ollama Ollama"))

    def test_load_reports_unreadable_encoding_and_size_limits(self):
        self.write("note.md", "Synthetic text")
        self.write("source.py", "not indexed")
        self.write(".env.txt", "excluded")
        self.write("nested/large.txt", "x" * 100)
        (self.root / "invalid.txt").write_bytes(b"\xff\xfeinvalid")
        self.write("binary.txt", "abc\0def")
        docs, skipped = load_text_documents(self.root, max_bytes=30)
        self.assertEqual([doc.source for doc in docs], ["note.md"])
        self.assertEqual(len(skipped), 3)

    def test_parameter_validation(self):
        with self.assertRaises(ValueError):
            BM25Index(self.docs, k1=0)
        with self.assertRaises(ValueError):
            BM25Index(self.docs, b=float("nan"))
        with self.assertRaises(ValueError):
            BM25Index(self.docs).search("query", limit=0)


class LinkTests(TemporaryWorkspace):
    def test_encoded_space_hash_and_chinese_targets(self):
        self.write("资料 #1.md", "# Note")
        self.write("README.md", '[note](<资料%20%231.md>)\n[fragment](#heading)\n[remote](https://example.com/missing)')
        result = check_links(self.root)
        self.assertEqual(result["checked_links"], 1)
        self.assertEqual(result["findings"], [])

    def test_missing_and_escaping_targets_with_line_numbers(self):
        self.write("README.md", "# Example\n\n[missing](missing.md)\n[escape](../outside.md)")
        result = check_links(self.root)
        self.assertEqual([row["line"] for row in result["findings"]], [3, 4])
        self.assertEqual([row["reason"] for row in result["findings"]],
                         ["missing target", "outside root"])

    def test_examples_inside_code_are_ignored(self):
        tick = chr(96)
        text = tick + "[inline](fake.md)" + tick + "\n"
        text += tick * 3 + "md\n[code](fake.md)\n" + tick * 3 + "\n"
        text += "~~~md\n[code](fake.md)\n~~~\n"
        self.write("README.md", text)
        self.assertEqual(check_links(self.root)["checked_links"], 0)

    def test_parentheses_images_and_title(self):
        self.write("note(v1).md", "Example")
        self.write("diagram.svg", "<svg/>")
        self.write("README.md", '[note](note(v1).md "Title")\n![image](diagram.svg)')
        self.assertEqual(check_links(self.root)["checked_links"], 2)
        self.assertEqual(check_links(self.root)["findings"], [])

    def test_windows_absolute_path_is_reported_on_all_platforms(self):
        self.write("README.md", "[machine](C:/private/note.md)")
        self.assertEqual(check_links(self.root)["findings"][0]["reason"], "absolute local path")


class CommandTests(TemporaryWorkspace):
    def invoke(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_catalog_and_search_json(self):
        self.write("note.md", "The demo uses Ollama 11434.")
        code, text, _ = self.invoke("catalog", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["totals"]["files"], 1)
        code, text, _ = self.invoke("search", str(self.root), "11434")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["results"][0]["source"], "note.md")

    def test_output_does_not_overwrite_existing_file(self):
        target = self.write("report.json", "keep me")
        code, _, error = self.invoke("catalog", str(self.root), "--output", str(target))
        self.assertEqual(code, 2)
        self.assertIn("already exists", error)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")

    def test_missing_root_and_invalid_limit_have_nonzero_exit(self):
        self.assertEqual(self.invoke("catalog", str(self.root / "missing"))[0], 2)
        self.assertEqual(self.invoke("search", str(self.root), "query", "--limit", "0")[0], 2)

    def test_extract_json_and_link_failure(self):
        docx = self.root / "sample.docx"
        create_sample(docx)
        code, text, _ = self.invoke("extract-docx", str(docx), "--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)[1]["kind"], "table")
        self.write("README.md", "[broken](missing.md)")
        self.assertEqual(self.invoke("check-links", str(self.root))[0], 1)


if __name__ == "__main__":
    unittest.main()
