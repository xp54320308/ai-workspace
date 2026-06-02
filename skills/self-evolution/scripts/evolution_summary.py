#!/usr/bin/env python3
"""
evolution_summary.py — 生成进化报告

用法:
  python evolution_summary.py
  python evolution_summary.py --days 7
  python evolution_summary.py --task-type wechat_posting
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta

CHROMA_DB_PATH = "/mnt/f/RAG_Project/chroma_db"
COLLECTION_NAME = "hermes_evolution"

def get_embedding_function():
    from chromadb import Documents, EmbeddingFunction, Embeddings
    
    class OllamaEmbeddingFunction(EmbeddingFunction):
        def __init__(self, url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
            self.url = url
            self.model = model

        def __call__(self, texts: Documents) -> Embeddings:
            import httpx
            embeddings = []
            for text in texts:
                response = httpx.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
            return embeddings

    return OllamaEmbeddingFunction()

def get_collection(ef):
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_collection(name=COLLECTION_NAME, embedding_function=ef)

def parse_doc(doc: str) -> dict:
    lines = doc.split("\n")
    parsed = {}
    for line in lines:
        if ": " in line:
            key, val = line.split(": ", 1)
            parsed[key.strip()] = val.strip()
    return parsed

def get_all_entries(collection, days: int = 7) -> list:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    try:
        results = collection.get(
            where={"timestamp": {"$gte": cutoff}},
            include=["documents", "metadatas"]
        )
    except Exception:
        # ChromaDB older API
        results = collection.get(
            include=["documents", "metadatas"]
        )
    
    entries = []
    if results["documents"]:
        for doc, meta in zip(results["documents"], results["metadatas"]):
            ts = meta.get("timestamp", "")
            if ts and ts < cutoff:
                continue
            entries.append({"document": doc, "metadata": meta, "parsed": parse_doc(doc)})
    
    return entries

def generate_report(entries: list, days: int) -> str:
    if not entries:
        return f"过去 {days} 天没有进化记录"
    
    lines = [f"# 📊 Hermes 自我进化报告（最近 {days} 天）", ""]
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**记录总数**: {len(entries)} 条")
    
    # 按任务类型分组
    by_type = defaultdict(list)
    by_outcome = defaultdict(int)
    
    for e in entries:
        p = e["parsed"]
        task_type = p.get("任务类型", e["metadata"].get("task_type", "unknown"))
        outcome = e["metadata"].get("outcome", "?")
        by_type[task_type].append(e)
        by_outcome[outcome] += 1
    
    # 总体统计
    lines.append("")
    lines.append("## 📈 总体统计")
    
    total = len(entries)
    success = by_outcome.get("success", 0)
    partial = by_outcome.get("partial", 0)
    failed = by_outcome.get("failed", 0)
    
    success_rate = success / total * 100 if total else 0
    
    lines.append(f"- 成功率: {success_rate:.0f}% （✅{success} ⚠️{partial} ❌{failed}）")
    lines.append(f"- 任务类型分布: {', '.join(f'{k}({len(v)})' for k, v in by_type.items())}")
    
    # 成功经验
    if success > 0:
        lines.append("")
        lines.append("## ✅ 成功经验（值得复用）")
        for e in entries:
            outcome = e["metadata"].get("outcome", "")
            if outcome == "success":
                p = e["parsed"]
                good = p.get("做得好", "")
                decisions = p.get("关键决策", "")
                advice = p.get("下次建议", "")
                ts = e["metadata"].get("timestamp", "")[:10]
                if good or advice:
                    lines.append(f"- **{p.get('任务类型','unknown')}** [{ts}]: {p.get('任务摘要','')[:40]}")
                    if decisions:
                        lines.append(f"  - 关键决策: {decisions}")
                    if good:
                        lines.append(f"  - 做得好: {good}")
                    if advice:
                        lines.append(f"  - 💡 复用: {advice}")
    
    # 失败教训
    if failed > 0:
        lines.append("")
        lines.append("## ❌ 失败教训（需要避免）")
        for e in entries:
            outcome = e["metadata"].get("outcome", "")
            if outcome == "failed":
                p = e["parsed"]
                improve = p.get("待改进", "")
                lessons = p.get("经验教训", "")
                advice = p.get("下次建议", "")
                ts = e["metadata"].get("timestamp", "")[:10]
                lines.append(f"- **{p.get('任务类型','unknown')}** [{ts}]: {p.get('任务摘要','')[:40]}")
                if improve:
                    lines.append(f"  - 问题: {improve}")
                if lessons:
                    lines.append(f"  - 教训: {lessons}")
                if advice:
                    lines.append(f"  - 下次: {advice}")
    
    # 部分成功
    if partial > 0:
        lines.append("")
        lines.append("## ⚠️ 部分成功（需要改进）")
        for e in entries:
            outcome = e["metadata"].get("outcome", "")
            if outcome == "partial":
                p = e["parsed"]
                improve = p.get("待改进", "")
                advice = p.get("下次建议", "")
                ts = e["metadata"].get("timestamp", "")[:10]
                lines.append(f"- **{p.get('任务类型','unknown')}** [{ts}]: {p.get('任务摘要','')[:40]}")
                if improve:
                    lines.append(f"  - 改进点: {improve}")
                if advice:
                    lines.append(f"  - 下次: {advice}")
    
    # 改进建议
    lines.append("")
    lines.append("## 🎯 改进建议")
    
    all_advice = []
    for e in entries:
        advice = e["parsed"].get("下次建议", "")
        if advice:
            all_advice.append(advice)
    
    if all_advice:
        # 去重并展示
        seen = set()
        for advice in all_advice:
            if advice not in seen:
                seen.add(advice)
                lines.append(f"- {advice}")
    else:
        lines.append("（暂无具体建议）")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="生成进化报告")
    parser.add_argument("--days", type=int, default=7, help="统计天数（默认7天）")
    parser.add_argument("--task-type", help="只看特定任务类型")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="输出格式")
    
    args = parser.parse_args()
    
    ef = get_embedding_function()
    collection = get_collection(ef)
    
    entries = get_all_entries(collection, days=args.days)
    
    if args.task_type:
        entries = [e for e in entries 
                   if e["parsed"].get("任务类型") == args.task_type 
                   or e["metadata"].get("task_type") == args.task_type]
    
    if args.format == "json":
        output = [{"metadata": e["metadata"], "parsed": e["parsed"]} for e in entries]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        report = generate_report(entries, days=args.days)
        print(report)

if __name__ == "__main__":
    main()
