"""Read DOCX body paragraphs and tables in order using only the standard library."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_XML_BYTES = 32 * 1024 * 1024


def _visible_text(node):
    if node.tag in {W + "del", W + "moveFrom"}:
        return ""
    if node.tag == W + "t":
        return node.text or ""
    if node.tag == W + "tab":
        return "\t"
    if node.tag in {W + "br", W + "cr"}:
        return "\n"
    parts = []
    for child in node:
        parts.append(_visible_text(child))
        if child.tag == W + "p":
            parts.append("\n")
    return "".join(parts)


def _body_blocks(node):
    for child in node:
        if child.tag in {W + "p", W + "tbl"}:
            yield child
        elif child.tag not in {W + "del", W + "moveFrom"}:
            yield from _body_blocks(child)


def extract_docx(path: Path, *, max_xml_bytes=MAX_XML_BYTES):
    """Return stable body-block IDs; omit comments, headers, and deleted text."""
    if max_xml_bytes < 1:
        raise ValueError("XML size limit must be positive")
    try:
        with ZipFile(path) as archive:
            info = archive.getinfo("word/document.xml")
            if info.file_size > max_xml_bytes:
                raise ValueError("DOCX body exceeds the XML size limit")
            with archive.open(info) as source:
                xml = source.read(max_xml_bytes + 1)
            if len(xml) > max_xml_bytes:
                raise ValueError("DOCX body exceeds the XML size limit")
    except (BadZipFile, KeyError) as error:
        raise ValueError("Expected a DOCX with word/document.xml") from error
    declaration_check = xml.replace(b"\x00", b"").upper()
    if b"<!DOCTYPE" in declaration_check or b"<!ENTITY" in declaration_check:
        raise ValueError("DTD and entity declarations are not supported")
    try:
        body = ET.fromstring(xml).find(W + "body")
    except ET.ParseError as error:
        raise ValueError("Invalid DOCX body XML") from error
    if body is None:
        raise ValueError("DOCX body is missing")
    blocks = []
    paragraph_no = table_no = 0
    for node in _body_blocks(body):
        if node.tag == W + "p":
            paragraph_no += 1
            text = _visible_text(node).strip()
            if text:
                style_node = node.find(f"{W}pPr/{W}pStyle")
                blocks.append({
                    "id": f"P{paragraph_no:03d}", "kind": "paragraph",
                    "style": style_node.get(W + "val", "") if style_node is not None else "",
                    "text": text,
                })
        else:
            table_no += 1
            rows = [[_visible_text(cell).strip() for cell in row.findall(W + "tc")]
                    for row in node.findall(W + "tr")]
            blocks.append({"id": f"T{table_no:03d}", "kind": "table", "rows": rows})
    return blocks


def render_blocks(blocks):
    """A readable text representation, also suitable as RAG input."""
    lines = []
    for block in blocks:
        if block["kind"] == "paragraph":
            lines.append(f'[{block["id"]}] {block["text"]}')
        else:
            lines.append(f'[{block["id"]}]')
            for number, row in enumerate(block["rows"], 1):
                cells = [value.replace("\n", " / ").replace("|", r"\|") for value in row]
                lines.append(f"[R{number:02d}] " + " | ".join(cells))
    return "\n\n".join(lines) + ("\n" if lines else "")
