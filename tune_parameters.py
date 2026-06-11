"""
参数调优脚本
"""

import json
import sys
sys.path.insert(0, '.')

import chromadb
import requests
from retrieval_evaluator import RetrievalEvaluator, GroundTruth


def get_embedding(text):
    resp = requests.post(
        'http://localhost:11434/api/embeddings',
        json={'model': 'nomic-embed-text', 'prompt': text},
        timeout=30
    )
    return resp.json()['embedding']


def load_benchmark(filepath="benchmark.json"):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("=" * 60)
    print("参数调优")
    print("=" * 60)
    
    benchmark = load_benchmark()
    client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
    collection = client.get_collection('langchain')
    
    k_values = [3, 5, 10]
    results = {}
    
    for k in k_values:
        print(f"\n测试 k={k}")
        test_cases = []
        
        for case in benchmark['test_cases']:
            query = case['query']
            relevant_ids = case['relevant_ids']
            relevance_levels = case.get('relevance_levels', {})
            
            query_embedding = get_embedding(query)
            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=['documents', 'metadatas']
            )
            
            retrieved_ids = search_results['ids'][0] if search_results['ids'] else []
            ground_truth = GroundTruth(query=query, relevant_ids=relevant_ids, relevance_levels=relevance_levels)
            test_cases.append((query, retrieved_ids, ground_truth))
        
        evaluator = RetrievalEvaluator()
        metrics = evaluator.evaluate_batch(test_cases, method=f"vector_k{k}")
        results[f"k={k}"] = metrics
        
        print(f"  Recall@{k}: {metrics.get('recall@' + str(k), 0):.4f}")
        print(f"  Precision@{k}: {metrics.get('precision@' + str(k), 0):.4f}")
        print(f"  MRR: {metrics.get('mrr', 0):.4f}")
    
    # 生成报告
    report = "# 参数调优报告\n\n"
    report += "## 评估结果\n\n"
    report += "| 参数 | Recall@K | Precision@K | MRR |\n"
    report += "|------|----------|-------------|-----|\n"
    
    for params, metrics in results.items():
        k = params.split('=')[1]
        report += "| {} | {:.4f} | {:.4f} | {:.4f} |\n".format(
            params,
            metrics.get('recall@' + k, 0),
            metrics.get('precision@' + k, 0),
            metrics.get('mrr', 0)
        )
    
    report += "\n## 优化建议\n\n"
    report += "1. 调整 k 值: 根据评估结果选择最佳 k 值\n"
    report += "2. 启用混合检索: 结合 BM25 提升关键词匹配\n"
    report += "3. 启用重排序: 使用 Cross-Encoder 提升准确率\n"
    report += "4. 启用查询扩展: 使用同义词扩展提升召回率\n"
    
    with open("tuning_report.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print("调优报告已保存: tuning_report.md")
    print("=" * 60)
    print(report)


if __name__ == "__main__":
    main()
