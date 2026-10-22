"""Check inline local Markdown links offline; never fetch external URLs."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit

from .catalog import walk_files

INLINE_LINK = re.compile(
    r'!?\[[^\]\n]*\]\(\s*(?:<([^>\n]+)>|((?:\\.|[^\\\s()]|\([^()\n]*\))+))'
    r'(?:\s+"[^"\n]*")?\s*\)'
)


def _without_code(text):
    result, fence = [], None
    fence_pattern = r"^ {0,3}(" + chr(96) + r"{3,}|~{3,})"
    inline_pattern = "(" + chr(96) + r"+).*?\1"
    for line in text.splitlines(keepends=True):
        marker = re.match(fence_pattern, line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            result.append("\n" if line.endswith("\n") else "")
        elif marker:
            fence = marker[1]
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(re.sub(inline_pattern, lambda m: " " * len(m[0]), line))
    return "".join(result)


def check_links(root: Path):
    """Check inline file/image targets, not anchors, reference links, or remote URLs."""
    root = Path(root).resolve(strict=True)
    findings, checked, markdown_files = [], 0, 0

    def on_error(error):
        findings.append({"source": "(unreadable directory)", "line": 0,
                         "target": "", "reason": type(error).__name__})

    for source in walk_files(root, on_error=on_error):
        if source.suffix.casefold() != ".md":
            continue
        markdown_files += 1
        try:
            text = _without_code(source.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError) as error:
            findings.append({"source": source.relative_to(root).as_posix(), "line": 0,
                             "target": "", "reason": type(error).__name__})
            continue
        for match in INLINE_LINK.finditer(text):
            target = match[1] or match[2]
            target = re.sub(r"\\([()\\])", r"\1", target)
            parts = urlsplit(target)
            if PureWindowsPath(target).is_absolute():
                checked += 1
                findings.append({
                    "source": source.relative_to(root).as_posix(),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "target": target, "reason": "absolute local path",
                })
                continue
            if parts.scheme or parts.netloc or not parts.path:
                continue
            decoded = unquote(parts.path)
            checked += 1
            resolved = (source.parent / decoded).resolve()
            reason = None
            if Path(decoded).is_absolute() or PureWindowsPath(decoded).is_absolute():
                reason = "absolute local path"
            elif not resolved.is_relative_to(root):
                reason = "outside root"
            elif not resolved.exists():
                reason = "missing target"
            if reason:
                findings.append({
                    "source": source.relative_to(root).as_posix(),
                    "line": text.count("\n", 0, match.start()) + 1,
                    "target": target, "reason": reason,
                })
    return {"markdown_files": markdown_files, "checked_links": checked, "findings": findings}
