#!/usr/bin/env python3
"""
log_evolution.py — 记录自我进化条目到 ChromaDB

用法:
  python log_evolution.py --type wechat_posting --summary "..." --outcome success \
    --decision "用了策略A" --good "封面生成快" --improve "标题公式要调整" \
    --lesson "IP白名单要提前加"

或交互模式:
  python log_evolution.py --interactive
"""

import argparse
import json
import sys
import os
from datetime import datetime

# ChromaDB setup
CHROMA_DB_PATH = "/mnt/f/RAG_Project/chroma_db"
COLLECTION_NAME = "hermes_evolution"

def get_embedding_function():
    try:
        from chromadb import Documents, EmbeddingFunction, Embeddings
        import httpx

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
    except ImportError as e:
        print(f"ERROR: chromadb not installed: {e}")
        sys.exit(1)

def get_collection(ef):
    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb not installed")
        sys.exit(1)
    
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=ef
        )
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
            metadata={"description": "Hermes self-evolution log"}
        )
    
    return collection

def build_document(entry: dict) -> str:
    """将 entry 构建为可检索的文本"""
    parts = [
        f"任务类型: {entry.get('task_type', 'unknown')}",
        f"任务摘要: {entry.get('task_summary', '')}",
        f"结果: {entry.get('outcome', 'unknown')}",
        f"关键决策: {'; '.join(entry.get('key_decisions', []))}",
        f"做得好: {'; '.join(entry.get('what_went_well', []))}",
        f"待改进: {'; '.join(entry.get('what_could_improve', []))}",
        f"经验教训: {'; '.join(entry.get('lessons', []))}",
        f"下次建议: {entry.get('next_time_advice', '')}",
    ]
    return "\n".join(parts)

def log_entry(entry: dict, collection) -> str:
    """写入一条进化记录"""
    import uuid
    
    doc = build_document(entry)
    entry_id = str(uuid.uuid4())[:8]
    
    collection.add(
        documents=[doc],
        metadatas=[{
            "task_type": entry.get("task_type", "unknown"),
            "outcome": entry.get("outcome", "unknown"),
            "timestamp": entry.get("timestamp", datetime.now().isoformat()),
        }],
        ids=[entry_id]
    )
    
    return entry_id

def interactive_input() -> dict:
    """引导式输入"""
    print("\n=== Hermes 自我进化记录 ===\n")
    
    task_type = input("任务类型 [wechat_posting/research/code/debug/other]: ").strip().lower() or "other"
    task_summary = input("任务摘要: ").strip()
    
    print("\n执行结果:")
    print("  1. 全部成功")
    print("  2. 部分成功")
    print("  3. 失败")
    outcome_map = {"1": "success", "2": "partial", "3": "failed"}
    outcome_choice = input("选择 [1-3]: ").strip()
    outcome = outcome_map.get(outcome_choice, "unknown")
    
    print("\n关键决策（用 ; 分隔多个）: ")
    decisions = [x.strip() for x in input().strip().split(";") if x.strip()]
    
    print("\n做得好（用 ; 分隔）: ")
    good = [x.strip() for x in input().strip().split(";") if x.strip()]
    
    print("\n待改进（用 ; 分隔）: ")
    improve = [x.strip() for x in input().strip().split(";") if x.strip()]
    
    print("\n经验教训（用 ; 分隔）: ")
    lessons = [x.strip() for x in input().strip().split(";") if x.strip()]
    
    next_advice = input("\n下次遇到类似任务建议: ").strip()
    
    return {
        "task_type": task_type,
        "task_summary": task_summary,
        "outcome": outcome,
        "key_decisions": decisions,
        "what_went_well": good,
        "what_could_improve": improve,
        "lessons": lessons,
        "next_time_advice": next_advice,
        "timestamp": datetime.now().isoformat(),
    }

def main():
    parser = argparse.ArgumentParser(description="记录自我进化条目")
    parser.add_argument("--type", help="任务类型")
    parser.add_argument("--summary", help="任务摘要")
    parser.add_argument("--outcome", help="结果: success/partial/failed")
    parser.add_argument("--decision", help="关键决策（; 分隔）")
    parser.add_argument("--good", help="做得好（; 分隔）")
    parser.add_argument("--improve", help="待改进（; 分隔）")
    parser.add_argument("--lesson", help="经验教训（; 分隔）")
    parser.add_argument("--advice", help="下次建议")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    parser.add_argument("--json", help="JSON格式输入")
    
    args = parser.parse_args()
    
    if args.json:
        entry = json.loads(args.json)
    elif args.interactive:
        entry = interactive_input()
    else:
        if not all([args.type, args.summary, args.outcome]):
            print("ERROR: 需要 --type, --summary, --outcome")
            print("或使用 --interactive 交互模式")
            sys.exit(1)
        
        entry = {
            "task_type": args.type,
            "task_summary": args.summary,
            "outcome": args.outcome,
            "key_decisions": [x.strip() for x in (args.decision or "").split(";") if x.strip()],
            "what_went_well": [x.strip() for x in (args.good or "").split(";") if x.strip()],
            "what_could_improve": [x.strip() for x in (args.improve or "").split(";") if x.strip()],
            "lessons": [x.strip() for x in (args.lesson or "").split(";") if x.strip()],
            "next_time_advice": args.advice or "",
            "timestamp": datetime.now().isoformat(),
        }
    
    ef = get_embedding_function()
    collection = get_collection(ef)
    entry_id = log_entry(entry, collection)
    
    print(f"\n✅ 进化记录已保存: {entry_id}")
    print(f"   任务: {entry['task_summary'][:50]}")
    print(f"   结果: {entry['outcome']}")
    print(f"   时间: {entry['timestamp']}")

if __name__ == "__main__":
    main()
