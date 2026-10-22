"""Small offline BM25 search adapted from the repository's RAG experiment branch."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .catalog import walk_files


def tokenize(text):
    """Case-insensitive words/numbers and Chinese characters plus bigrams."""
    terms = re.findall(r"[a-z0-9_]+", text.casefold())
    for span in re.findall(r"[\u4e00-\u9fff]+", text):
        terms.extend(span)
        terms.extend(span[i:i + 2] for i in range(len(span) - 1))
    return terms


@dataclass(frozen=True)
class SearchDocument:
    source: str
    text: str


class BM25Index:
    def __init__(self, documents, *, k1=1.5, b=0.75):
        if not math.isfinite(k1) or k1 <= 0 or not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("Require finite k1 > 0 and 0 <= b <= 1")
        self.documents = list(documents)
        self.k1, self.b = k1, b
        self.frequencies = [Counter(tokenize(doc.text)) for doc in self.documents]
        self.lengths = [sum(freq.values()) for freq in self.frequencies]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        occurrences = Counter(term for freq in self.frequencies for term in freq)
        self.idf = {term: math.log(1 + (len(self.documents) - count + 0.5) / (count + 0.5))
                    for term, count in occurrences.items()}

    def search(self, query, *, limit=5):
        if limit < 1:
            raise ValueError("Search limit must be positive")
        terms = set(tokenize(query))
        results = []
        for index, (doc, freq) in enumerate(zip(self.documents, self.frequencies)):
            score = 0.0
            if self.average_length:
                norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average_length)
                for term in terms:
                    count = freq[term]
                    if count:
                        score += self.idf[term] * count * (self.k1 + 1) / (count + norm)
            if score > 0:
                results.append({"source": doc.source, "score": round(score, 6),
                                "snippet": _snippet(doc.text, terms), "_order": index})
        results.sort(key=lambda row: (-row["score"], row["_order"]))
        return [{key: value for key, value in row.items() if key != "_order"}
                for row in results[:limit]]


def _snippet(text, terms, size=240):
    positions = [text.casefold().find(term) for term in terms]
    positions = [value for value in positions if value >= 0]
    start = max(0, min(positions, default=0) - 60)
    return ("…" if start else "") + text[start:start + size].replace("\n", " ")


def load_text_documents(root: Path, *, max_bytes=2 * 1024 * 1024):
    """Read only UTF-8 Markdown/text, with explicit reporting for skipped files."""
    if max_bytes < 1:
        raise ValueError("Text size limit must be positive")
    root = Path(root).resolve(strict=True)
    documents, skipped = [], []

    def on_error(error):
        skipped.append({"source": "(unreadable directory)", "reason": type(error).__name__})

    for path in walk_files(root, on_error=on_error):
        if path.suffix.casefold() not in {".txt", ".md"}:
            continue
        source = path.relative_to(root).as_posix()
        try:
            with path.open("rb") as stream:
                raw = stream.read(max_bytes + 1)
            if len(raw) > max_bytes:
                skipped.append({"source": source, "reason": "size limit"})
                continue
            text = raw.decode("utf-8-sig")
            if "\0" in text:
                skipped.append({"source": source, "reason": "binary content"})
                continue
        except (OSError, UnicodeError) as error:
            skipped.append({"source": source, "reason": type(error).__name__})
            continue
        documents.append(SearchDocument(source, text))
    return documents, skipped
