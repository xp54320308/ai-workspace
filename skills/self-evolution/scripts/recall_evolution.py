#!/usr/bin/env python3
"""
recall_evolution.py — 从 ChromaDB 检索相关进化经验

用法:
  python recall_evolution.py --query "微信发文失败"
  python recall_evolution.py --task-type wechat_posting
  python recall_evolution.py --interactive
"""

import argparse
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

def format_entry(doc: str, metadata) -> str:
    if isinstance(metadata, list):
        metadata = metadata[0] if metadata else {}
    
    outcome_emoji = {"success": "✅", "partial": "⚠️", "failed": "❌"}
    outcome = metadata.get("outcome", "") if isinstance(metadata, dict) else ""
    emoji = outcome_emoji.get(outcome, "❓")
    ts = metadata.get("timestamp", "") if isinstance(metadata, dict) else ""
    try:
        dt = datetime.fromisoformat(ts)
        ts = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    
    parsed = parse_doc(doc)
    task_type = parsed.get("任务类型", metadata.get("task_type", "unknown") if isinstance(metadata, dict) else "")
    task_summary = parsed.get("任务摘要", "")
    
    output = [f"{emoji} [{ts}] {task_type}: {task_summary}"]
    
    decisions = parsed.get("关键决策", "")
    good = parsed.get("做得好", "")
    improve = parsed.get("待改进", "")
    lessons = parsed.get("经验教训", "")
    advice = parsed.get("下次建议", "")
    
    if decisions:
        output.append(f"   决策: {decisions}")
    if good:
        output.append(f"   ✅ {good}")
    if lessons:
        output.append(f"   📝 {lessons}")
    if improve:
        output.append(f"   🔧 {improve}")
    if advice:
        output.append(f"   💡 下次: {advice}")
    
    return "\n".join(output)

def recall(query: str, collection, limit: int = 5) -> list:
    """向量检索"""
    results = collection.query(
        query_texts=[query],
        n_results=limit,
        include=["documents", "metadatas"]
    )
    
    entries = []
    docs_list = results.get("documents", [[]])[0] if results.get("documents") else []
    metas_list = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    
    for doc, meta in zip(docs_list, metas_list):
        entries.append({"document": doc, "metadata": meta})
    
    return entries

def recall_by_task_type(task_type: str, collection, limit: int = 10, days: int = 30) -> list:
    """按任务类型+时间过滤"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    try:
        results = collection.get(
            where={
                "$and": [
                    {"task_type": {"$eq": task_type}},
                    {"timestamp": {"$gte": cutoff}}
                ]
            },
            limit=limit,
            include=["documents", "metadatas"]
        )
    except Exception:
        results = collection.get(include=["documents", "metadatas"])
    
    entries = []
    docs_list = results.get("documents", [])
    metas_list = results.get("metadatas", [])
    
    for doc, meta in zip(docs_list, metas_list):
        ts = meta.get("timestamp", "") if isinstance(meta, dict) else ""
        if ts and ts < cutoff:
            continue
        entries.append({"document": doc, "metadata": meta, "parsed": parse_doc(doc)})
    
    return entries

def main():
    parser = argparse.ArgumentParser(description="检索自我进化经验")
    parser.add_argument("--query", help="自然语言查询")
    parser.add_argument("--task-type", help="按任务类型筛选")
    parser.add_argument("--limit", type=int, default=5, help="返回数量")
    parser.add_argument("--days", type=int, default=30, help="时间范围（天）")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    ef = get_embedding_function()
    collection = get_collection(ef)
    
    if args.task_type:
        entries = recall_by_task_type(args.task_type, collection, limit=args.limit, days=args.days)
        if not entries:
            print(f"没有找到 {args.task_type} 的经验记录")
            return
        for i, entry in enumerate(entries, 1):
            print(f"--- 经验 {i} ---")
            print(format_entry(entry["document"], entry["metadata"]))
            print()
    else:
        if not args.query:
            print("需要 --query 或 --task-type")
            return
        entries = recall(args.query, collection, limit=args.limit)
        if not entries:
            print("没有找到相关经验记录")
            return
        for i, entry in enumerate(entries, 1):
            print(f"--- 相关经验 {i} ---")
            print(format_entry(entry["document"], entry["metadata"]))
            print()

if __name__ == "__main__":
    main()
