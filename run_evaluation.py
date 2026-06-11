"""
运行评估对比

对比不同检索策略的效果
"""

import json
import time
import sys
sys.path.insert(0, '.')

import chromadb
import requests
from pathlib import Path
from retrieval_evaluator import RetrievalEvaluator, GroundTruth


def get_embedding(text):
    """获取 embedding"""
    resp = requests.post(
        'http://localhost:11434/api/embeddings',
        json={'model': 'nomic-embed-text', 'prompt': text},
        timeout=30
    )
    return resp.json()['embedding']


def load_benchmark(filepath="benchmark.json"):
    """加载基准测试数据集"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def vector_search(query, collection, k=10):
    """向量检索"""
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=['documents', 'metadatas']
    )
    return results['ids'][0] if results['ids'] else []


def run_evaluation():
    """运行评估"""
    print("=" * 60)
    print("运行检索评估")
    print("=" * 60)
    
    # 加载基准测试
    benchmark = load_benchmark()
    print(f"\n基准测试用例数: {len(benchmark['test_cases'])}")
    
    # 连接向量库
    client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
    collection = client.get_collection('langchain')
    print(f"向量库文档数: {collection.count()}")
    
    # 创建评估器
    evaluator = RetrievalEvaluator(output_dir="eval_results")
    
    # 评估向量检索
    print("\n--- 评估向量检索 ---")
    test_cases = []
    
    for case in benchmark['test_cases']:
        query = case['query']
        relevant_ids = case['relevant_ids']
        relevance_levels = case.get('relevance_levels', {})
        
        # 执行向量检索
        start_time = time.time()
        retrieved_ids = vector_search(query, collection, k=10)
        latency_ms = (time.time() - start_time) * 1000
        
        ground_truth = GroundTruth(
            query=query,
            relevant_ids=relevant_ids,
            relevance_levels=relevance_levels
        )
        
        test_cases.append((query, retrieved_ids, ground_truth))
        print(f"  查询: {query}")
        print(f"    检索到: {len(retrieved_ids)} 个文档")
        print(f"    相关文档: {len(relevant_ids)} 个")
        print(f"    延迟: {latency_ms:.2f} ms")
    
    # 批量评估
    metrics = evaluator.evaluate_batch(test_cases, method="vector")
    
    print("\n向量检索评估结果:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value:.4f}")
    
    # 保存结果
    evaluator.save_results("vector_evaluation.json")
    
    return metrics


if __name__ == "__main__":
    metrics = run_evaluation()
    print("\n✅ 评估完成")
