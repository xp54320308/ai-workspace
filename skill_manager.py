"""Local skill memory for saved RAG question/answer pairs.

The manager stores a small JSON index under ``skills/`` by default. It is
deliberately simple so the project can run without an extra database service.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SkillManager:
    """Manage locally saved question/answer skills."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.index_path = self.skills_dir / "index.json"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()

    def save_skill(
        self,
        question: str,
        answer: str,
        sources: Optional[Iterable[str]] = None,
        rating: int = 5,
        tags: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """Save a reusable Q&A skill and return its metadata."""

        skill_id = f"skill-{uuid.uuid4().hex[:12]}"
        now = _utc_now()
        normalized_rating = max(1, min(5, int(rating)))
        source_list = sorted(set(sources or []))
        tag_list = sorted(set(tags or []))
        keywords = _keywords(question)

        record = {
            "skill_id": skill_id,
            "question": question,
            "answer": answer,
            "sources": source_list,
            "rating": normalized_rating,
            "tags": tag_list,
            "keywords": keywords,
            "hits": 0,
            "created": now,
            "updated": now,
        }

        self._index["skills"].append(record)
        self._index["last_updated"] = now
        self._write_index()
        return record

    def search_skills(self, query: str, min_rating: int = 4) -> List[Dict[str, Any]]:
        """Return matching skills ordered by simple lexical overlap."""

        query_terms = set(_keywords(query))
        if not query_terms:
            return []

        matches = []
        for skill in self._index.get("skills", []):
            if int(skill.get("rating", 0)) < min_rating:
                continue

            skill_terms = set(skill.get("keywords") or _keywords(skill.get("question", "")))
            if not skill_terms:
                continue

            overlap = query_terms & skill_terms
            score = len(overlap) / max(len(query_terms), 1)
            if score > 0:
                item = dict(skill)
                item["score"] = round(score, 4)
                matches.append(item)

        return sorted(matches, key=lambda item: (item["score"], item.get("rating", 0)), reverse=True)

    def get_skill_answer(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Return a skill by ID and increment its hit count."""

        for skill in self._index.get("skills", []):
            if skill.get("skill_id") == skill_id:
                skill["hits"] = int(skill.get("hits", 0)) + 1
                skill["updated"] = _utc_now()
                self._index["last_updated"] = skill["updated"]
                self._write_index()
                return dict(skill)
        return None

    def list_skills(self, sort_by: str = "created") -> List[Dict[str, Any]]:
        """List all skills sorted by a known metadata field."""

        valid_sort_keys = {"created", "updated", "rating", "hits", "question"}
        key = sort_by if sort_by in valid_sort_keys else "created"
        reverse = key in {"created", "updated", "rating", "hits"}
        return sorted(self._index.get("skills", []), key=lambda item: item.get(key, ""), reverse=reverse)

    def delete_skill(self, skill_id: str) -> bool:
        """Remove an obsolete answer from the index and persist the change."""
        remaining = [
            skill for skill in self._index["skills"]
            if skill.get("skill_id") != skill_id
        ]
        if len(remaining) == len(self._index["skills"]):
            return False
        self._index["skills"] = remaining
        self._index["last_updated"] = _utc_now()
        self._write_index()
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate skill-memory statistics."""

        skills = self._index.get("skills", [])
        total = len(skills)
        total_hits = sum(int(skill.get("hits", 0)) for skill in skills)
        avg_rating = round(sum(int(skill.get("rating", 0)) for skill in skills) / total, 2) if total else 0

        return {
            "total_skills": total,
            "total_hits": total_hits,
            "avg_rating": avg_rating,
            "last_updated": self._index.get("last_updated"),
        }

    def _load_index(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {"version": 1, "last_updated": None, "skills": []}

        with self.index_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("version", 1)
        data.setdefault("last_updated", None)
        data.setdefault("skills", [])
        return data

    def _write_index(self) -> None:
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)


def _keywords(text: str) -> List[str]:
    """Extract simple multilingual keywords for local matching."""

    text = text.lower()
    ascii_terms = re.findall(r"[a-z0-9][a-z0-9_-]{1,}", text)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]", text)
    terms = ascii_terms + cjk_terms
    return sorted(set(terms))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
