"""
创建基准测试数据集

基于现有向量库数据，创建真实的测试用例
"""

import json
import chromadb
import requests
from pathlib import Path


def get_embedding(text):
    """获取 embedding"""
    resp = requests.post(
        'http://localhost:11434/api/embeddings',
        json={'model': 'nomic-embed-text', 'prompt': text},
        timeout=30
    )
    return resp.json()['embedding']


def search_documents(query, n_results=10):
    """搜索文档"""
    client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
    collection = client.get_collection('langchain')
    
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['documents', 'metadatas']
    )
    
    return results


def create_benchmark():
    """创建基准测试数据集"""
    benchmark = {
        "version": "1.0",
        "description": "RAG 项目基准测试数据集",
        "test_cases": []
    }
    
    # 测试用例 1: 合同价格
    print("\n=== 测试用例 1: 合同价格 ===")
    results = search_documents("合同价格 签约合同价", n_results=10)
    
    # 手动标注相关文档
    relevant_ids = []
    relevance_levels = {}
    
    for i, (doc, meta, doc_id) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['ids'][0]
    )):
        print(f"\n[{i+1}] ID: {doc_id}")
        print(f"    来源: {meta.get('source_file', 'unknown')}")
        print(f"    内容: {doc[:100]}...")
        
        # 判断是否相关
        if '合同价' in doc or '签约' in doc or '7.798' in doc or '779809858' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 3 if '7.798' in doc or '779809858' in doc else 2
            print(f"    -> 相关 (level: {relevance_levels[doc_id]})")
        elif '工期' in doc or '1643' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 1
            print(f"    -> 部分相关 (level: 1)")
    
    if relevant_ids:
        benchmark["test_cases"].append({
            "query": "合同价格是多少",
            "relevant_ids": relevant_ids,
            "relevance_levels": relevance_levels,
            "description": "查询合同签约价格"
        })
    
    # 测试用例 2: 工期
    print("\n=== 测试用例 2: 工期 ===")
    results = search_documents("工期 施工期限", n_results=10)
    
    relevant_ids = []
    relevance_levels = {}
    
    for i, (doc, meta, doc_id) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['ids'][0]
    )):
        print(f"\n[{i+1}] ID: {doc_id}")
        print(f"    来源: {meta.get('source_file', 'unknown')}")
        print(f"    内容: {doc[:100]}...")
        
        if '工期' in doc or '1643' in doc or '天' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 3 if '1643' in doc else 2
            print(f"    -> 相关 (level: {relevance_levels[doc_id]})")
    
    if relevant_ids:
        benchmark["test_cases"].append({
            "query": "工期是多少天",
            "relevant_ids": relevant_ids,
            "relevance_levels": relevance_levels,
            "description": "查询施工工期"
        })
    
    # 测试用例 3: 合同条款
    print("\n=== 测试用例 3: 合同条款 ===")
    results = search_documents("合同条款 通用条款", n_results=10)
    
    relevant_ids = []
    relevance_levels = {}
    
    for i, (doc, meta, doc_id) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['ids'][0]
    )):
        print(f"\n[{i+1}] ID: {doc_id}")
        print(f"    来源: {meta.get('source_file', 'unknown')}")
        print(f"    内容: {doc[:100]}...")
        
        if '条款' in doc or '合同' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 2
            print(f"    -> 相关 (level: 2)")
    
    if relevant_ids:
        benchmark["test_cases"].append({
            "query": "合同条款有哪些",
            "relevant_ids": relevant_ids[:5],  # 限制数量
            "relevance_levels": {k: v for k, v in list(relevance_levels.items())[:5]},
            "description": "查询合同条款"
        })
    
    # 测试用例 4: 投标
    print("\n=== 测试用例 4: 投标 ===")
    results = search_documents("投标 投标文件", n_results=10)
    
    relevant_ids = []
    relevance_levels = {}
    
    for i, (doc, meta, doc_id) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['ids'][0]
    )):
        print(f"\n[{i+1}] ID: {doc_id}")
        print(f"    来源: {meta.get('source_file', 'unknown')}")
        print(f"    内容: {doc[:100]}...")
        
        if '投标' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 2
            print(f"    -> 相关 (level: 2)")
    
    if relevant_ids:
        benchmark["test_cases"].append({
            "query": "投标文件要求",
            "relevant_ids": relevant_ids[:5],
            "relevance_levels": {k: v for k, v in list(relevance_levels.items())[:5]},
            "description": "查询投标要求"
        })
    
    # 测试用例 5: 设计
    print("\n=== 测试用例 5: 设计 ===")
    results = search_documents("设计 初步设计", n_results=10)
    
    relevant_ids = []
    relevance_levels = {}
    
    for i, (doc, meta, doc_id) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['ids'][0]
    )):
        print(f"\n[{i+1}] ID: {doc_id}")
        print(f"    来源: {meta.get('source_file', 'unknown')}")
        print(f"    内容: {doc[:100]}...")
        
        if '设计' in doc:
            relevant_ids.append(doc_id)
            relevance_levels[doc_id] = 2
            print(f"    -> 相关 (level: 2)")
    
    if relevant_ids:
        benchmark["test_cases"].append({
            "query": "设计方案",
            "relevant_ids": relevant_ids[:5],
            "relevance_levels": {k: v for k, v in list(relevance_levels.items())[:5]},
            "description": "查询设计方案"
        })
    
    return benchmark


def save_benchmark(benchmark, filepath="benchmark.json"):
    """保存基准测试数据集"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)
    
    print(f"\n基准测试数据集已保存: {filepath}")
    print(f"测试用例数: {len(benchmark['test_cases'])}")


if __name__ == "__main__":
    print("=== 创建基准测试数据集 ===")
    
    benchmark = create_benchmark()
    save_benchmark(benchmark, "benchmark.json")
    
    print("\n✅ 基准测试数据集创建完成")
