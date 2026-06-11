"""
闭环学习管理器 — 将高质量 RAG 问答保存为可复用的 Skill

借鉴 CLI-Anything 的 SKILL.md 模式：
- 每个 Skill 是一个独立的 .md 文件
- 包含问题、答案、来源、元数据
- 下次遇到相似问题时可直接匹配，跳过 RAG 检索

工作流程:
  用户提问 → RAG 检索 → LLM 回答 → 用户反馈评分
      ↓ (高质量问答)
  保存为 Skill → 下次直接匹配
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path


class SkillManager:
    """管理 RAG 闭环学习的 Skill 文件"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.skills_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> dict:
        """加载 Skill 索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"skills": {}, "total": 0, "last_updated": None}

    def _save_index(self):
        """保存 Skill 索引"""
        self.index["last_updated"] = datetime.now().isoformat()
        self.index["total"] = len(self.index["skills"])
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def _generate_skill_id(self, question: str) -> str:
        """从问题生成唯一 Skill ID"""
        # 取前30个字符 + hash 保证唯一
        slug = re.sub(r'[^\w\u4e00-\u9fff]', '_', question[:30]).strip('_')
        hash_suffix = hashlib.md5(question.encode()).hexdigest()[:6]
        return f"{slug}_{hash_suffix}"

    def _extract_keywords(self, text: str) -> list:
        """从文本中提取关键词（中英文混合）"""
        # 中文词汇（连续的中文字符）
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        # 英文词汇
        en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        # 去重
        return list(set(cn_words + en_words))

    def save_skill(
        self,
        question: str,
        answer: str,
        sources: list = None,
        docs: list = None,
        rating: int = 5,
        tags: list = None,
    ) -> str:
        """
        将问答对保存为 Skill 文件

        Args:
            question: 用户问题
            answer: RAG 回答
            sources: 来源文件列表
            docs: 检索到的文档块
            rating: 用户评分 (1-5)
            tags: 自定义标签

        Returns:
            保存的 Skill 文件路径
        """
        skill_id = self._generate_skill_id(question)
        skill_file = self.skills_dir / f"{skill_id}.md"
        keywords = self._extract_keywords(question)

        # 构建来源信息
        source_text = ""
        if sources:
            source_text = "\n".join(f"- {s}" for s in sources)

        # 构建 Skill 文件内容
        content = f"""---
name: {skill_id}
question: |
  {question}
keywords: {json.dumps(keywords, ensure_ascii=False)}
sources: {json.dumps(sources or [], ensure_ascii=False)}
tags: {json.dumps(tags or [], ensure_ascii=False)}
rating: {rating}
created: {datetime.now().isoformat()}
hits: 0
---

# Q: {question}

## A

{answer}

## 来源

{source_text if source_text else "无"}
"""

        # 写入文件
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(content)

        # 更新索引
        self.index["skills"][skill_id] = {
            "file": f"{skill_id}.md",
            "question": question[:100],
            "keywords": keywords[:10],
            "sources": sources or [],
            "rating": rating,
            "created": datetime.now().isoformat(),
            "hits": 0,
        }
        self._save_index()

        print(f"💾 Skill 已保存: {skill_file}")
        return str(skill_file)

    def search_skills(self, query: str, min_rating: int = 0, top_k: int = 3) -> list:
        """
        搜索匹配的 Skills

        使用关键词重叠度评分，返回最匹配的 Skills。

        Args:
            query: 用户查询
            min_rating: 最低评分过滤
            top_k: 返回数量

        Returns:
            匹配的 Skill 列表 [{"skill_id", "question", "answer", "score", "file"}]
        """
        query_keywords = set(self._extract_keywords(query))
        if not query_keywords:
            return []

        matches = []
        for skill_id, meta in self.index["skills"].items():
            if meta.get("rating", 0) < min_rating:
                continue

            skill_keywords = set(meta.get("keywords", []))
            # 计算关键词重叠度
            overlap = len(query_keywords & skill_keywords)
            if overlap == 0:
                continue

            # Jaccard 相似度
            union = len(query_keywords | skill_keywords)
            score = overlap / union if union > 0 else 0

            if score > 0:
                matches.append({
                    "skill_id": skill_id,
                    "question": meta["question"],
                    "score": round(score, 3),
                    "file": meta["file"],
                    "rating": meta.get("rating", 0),
                    "hits": meta.get("hits", 0),
                })

        # 按分数降序排列
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_k]

    def get_skill_answer(self, skill_id: str) -> dict:
        """读取 Skill 文件获取完整问答"""
        skill_file = self.skills_dir / f"{skill_id}.md"
        if not skill_file.exists():
            return None

        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                meta = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()

                # 更新命中次数
                meta["hits"] = meta.get("hits", 0) + 1
                self.index["skills"][skill_id]["hits"] = meta["hits"]
                self._save_index()

                return {
                    "skill_id": skill_id,
                    "question": meta.get("question", ""),
                    "answer": body,
                    "sources": meta.get("sources", []),
                    "rating": meta.get("rating", 0),
                    "hits": meta["hits"],
                }
        return None

    def list_skills(self, sort_by: str = "created") -> list:
        """列出所有 Skills"""
        skills = []
        for skill_id, meta in self.index["skills"].items():
            skills.append({
                "skill_id": skill_id,
                **meta,
            })

        if sort_by == "hits":
            skills.sort(key=lambda x: x.get("hits", 0), reverse=True)
        elif sort_by == "rating":
            skills.sort(key=lambda x: x.get("rating", 0), reverse=True)
        else:
            skills.sort(key=lambda x: x.get("created", ""), reverse=True)

        return skills

    def delete_skill(self, skill_id: str) -> bool:
        """删除一个 Skill"""
        skill_file = self.skills_dir / f"{skill_id}.md"
        if skill_file.exists():
            skill_file.unlink()
        if skill_id in self.index["skills"]:
            del self.index["skills"][skill_id]
            self._save_index()
            return True
        return False

    def get_stats(self) -> dict:
        """获取 Skill 统计信息"""
        skills = self.index.get("skills", {})
        total = len(skills)
        total_hits = sum(s.get("hits", 0) for s in skills.values())
        avg_rating = (
            sum(s.get("rating", 0) for s in skills.values()) / total
            if total > 0 else 0
        )
        return {
            "total_skills": total,
            "total_hits": total_hits,
            "avg_rating": round(avg_rating, 1),
            "last_updated": self.index.get("last_updated"),
        }


# 便捷函数
def quick_save(question: str, answer: str, sources: list = None, rating: int = 5):
    """快速保存 Skill"""
    mgr = SkillManager()
    return mgr.save_skill(question, answer, sources=sources, rating=rating)


def quick_search(query: str):
    """快速搜索 Skills"""
    mgr = SkillManager()
    return mgr.search_skills(query)
