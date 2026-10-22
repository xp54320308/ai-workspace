"""CLI for the dependency-free workspace tools."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import build_catalog
from .docx import extract_docx, render_blocks
from .links import check_links
from .search import BM25Index, load_text_documents


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m workspace_tools")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="Inventory metadata without reading file contents")
    catalog.add_argument("root", type=Path)
    catalog.add_argument("--depth", type=int, default=2)
    catalog.add_argument("--exclude", action="append", default=[], metavar="DIR_NAME")
    extract = commands.add_parser("extract-docx", help="Extract DOCX paragraphs and tables in order")
    extract.add_argument("source", type=Path)
    extract.add_argument("--format", choices=("text", "json"), default="text")
    search = commands.add_parser("search", help="Search UTF-8 .md/.txt locally with BM25")
    search.add_argument("root", type=Path)
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    links = commands.add_parser("check-links", help="Check inline local Markdown file/image links")
    links.add_argument("root", type=Path)
    for command in (catalog, extract, search, links):
        command.add_argument("--output", type=Path, help="Write report instead of printing")
    args = parser.parse_args(argv)
    try:
        if args.output:
            target = args.output.resolve()
            protected = args.source if args.command == "extract-docx" else args.root
            if target == protected.resolve():
                raise ValueError("Output cannot overwrite the input")
            if target.exists():
                raise ValueError("Output already exists; choose a new path")
        code = 0
        if args.command == "catalog":
            result = build_catalog(args.root, depth=args.depth, exclude=args.exclude)
            code = 1 if result["errors"] else 0
        elif args.command == "extract-docx":
            blocks = extract_docx(args.source)
            result = blocks if args.format == "json" else render_blocks(blocks)
        elif args.command == "search":
            documents, skipped = load_text_documents(args.root)
            result = {"indexed_documents": len(documents), "skipped": skipped,
                      "results": BM25Index(documents).search(args.query, limit=args.limit)}
            code = 1 if skipped else 0
        else:
            result = check_links(args.root)
            code = 1 if result["findings"] else 0
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(output)
        else:
            sys.stdout.write(output)
        return code
    except (OSError, ValueError) as error:
        print(f"workspace_tools: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
