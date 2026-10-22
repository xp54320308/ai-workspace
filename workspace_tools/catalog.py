"""Inventory files without reading their contents or following directory links."""

from __future__ import annotations

import os
import stat
from collections import Counter
from pathlib import Path

EXCLUDED_DIRS = frozenset({
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next", ".cache",
    ".deps", "site-packages", "dist-packages", "vendor", "payload",
    "chroma_db", "vectorstore", "edge-profile", "ocr-packages",
})
CODE_EXTENSIONS = {".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".ps1", ".sh"}
DOCUMENT_EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx"}
PRIVATE_NAMES = {"auth.json", "credentials.json", "config.yaml", "id_rsa", "id_ed25519"}


def _is_link(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def is_excluded_file(path: Path) -> bool:
    name = path.name.casefold()
    return (
        name in PRIVATE_NAMES or name == ".env" or name.startswith(".env.")
        or path.suffix.casefold() in {".pem", ".key", ".sqlite", ".sqlite3", ".db"}
    )


def walk_files(root: Path, *, exclude=(), on_error=None):
    """Yield deterministic paths. Directory junctions and file links are skipped."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Root must be a directory")
    skipped = EXCLUDED_DIRS | {name.casefold() for name in exclude}
    for current, dirs, files in os.walk(root, followlinks=False, onerror=on_error):
        dirs[:] = sorted(
            name for name in dirs
            if name.casefold() not in skipped
            and not name.startswith(".")
            and not _is_link(Path(current) / name)
        )
        for name in sorted(files):
            path = Path(current) / name
            if _is_link(path) or is_excluded_file(path):
                continue
            yield path


def build_catalog(root: Path, *, depth=2, exclude=()):
    """Group metadata by relative path; paths can still be private."""
    if depth < 1:
        raise ValueError("Project depth must be at least 1")
    root = Path(root).resolve(strict=True)
    projects = {}
    errors = []

    def record_error(error):
        errors.append({"path": _relative(Path(error.filename), root), "error": type(error).__name__})

    for path in walk_files(root, exclude=exclude, on_error=record_error):
        rel = path.relative_to(root)
        group = "/".join(rel.parts[:-1][:depth]) or "."
        item = projects.setdefault(group, {
            "path": group, "files": 0, "bytes": 0, "code_files": 0,
            "document_files": 0, "extensions": Counter(), "markers": [],
        })
        try:
            size = path.stat().st_size
        except OSError as error:
            errors.append({"path": rel.as_posix(), "error": type(error).__name__})
            continue
        suffix = path.suffix.casefold() or "(none)"
        item["files"] += 1
        item["bytes"] += size
        item["code_files"] += int(suffix in CODE_EXTENSIONS)
        item["document_files"] += int(suffix in DOCUMENT_EXTENSIONS)
        item["extensions"][suffix] += 1
        if path.name in {"README.md", "LICENSE", "package.json", "pyproject.toml", "requirements.txt"}:
            item["markers"].append(rel.as_posix())
    rows = []
    for key in sorted(projects):
        item = projects[key]
        item["extensions"] = dict(sorted(item["extensions"].items()))
        rows.append(item)
    return {
        "schema_version": 1,
        "scope": "File metadata only; not proof of authorship, maintenance, or adoption.",
        "projects": rows,
        "totals": {key: sum(row[key] for row in rows)
                   for key in ("files", "bytes", "code_files", "document_files")},
        "errors": errors,
    }


def _relative(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return "(outside root)"
