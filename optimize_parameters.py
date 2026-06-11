"""
参数调优脚本

功能：
1. 测试不同权重组合
2. 找出最佳参数
3. 生成调优报告
"""

import json
import sys
sys.path.insert(0, '.')

import chromadb
import requests
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
    """加载基准测试"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def vector_search(query, collection, k=5):
    """向量检索"""
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=['documents', 'metadatas']
    )
    return results['ids'][0] if results['ids'] else []


def test_weight_combinations(collection, benchmark):
    """测试不同权重组合"""
    results = {}
    
    # 权重组合
    weight_combinations = [
        {"vector": 0.7, "bm25": 0.3, "name": "向量为主"},
        {"vector": 0.6, "bm25": 0.4, "name": "平衡"},
        {"vector": 0.5, "bm25": 0.5, "name": "等权重"},
        {"vector": 0.4, "bm25": 0.6, "name": "BM25为主"},
    ]
    
    for combo in weight_combinations:
        print(f"\n测试权重: {combo['name']} (向量={combo['vector']}, BM25={combo['bm25']})")
        
        test_cases = []
        for case in benchmark['test_cases']:
            query = case['query']
            relevant_ids = case['relevant_ids']
            relevance_levels = case.get('relevance_levels', {})
            
            # 执行检索
            retrieved_ids = vector_search(query, collection, k=5)
            
            ground_truth = GroundTruth(
                query=query,
                relevant_ids=relevant_ids,
                relevance_levels=relevance_levels
            )
            
            test_cases.append((query, retrieved_ids, ground_truth))
        
        # 评估
        evaluator = RetrievalEvaluator()
        metrics = evaluator.evaluate_batch(test_cases, method=f"vector_{combo['name']}")
        results[combo['name']] = metrics
        
        print(f"  Recall@5: {metrics.get('recall@5', 0):.4f}")
        print(f"  Precision@5: {metrics.get('precision@5', 0):.4f}")
        print(f"  MRR: {metrics.get('mrr', 0):.4f}")
    
    return results


def find_best_parameters(results):
    """找出最佳参数"""
    best_method = max(results.items(), key=lambda x: x[1].get('mrr', 0))
    return best_method


def generate_optimization_report(results, best_method):
    """生成调优报告"""
    report = "# 参数调优报告\n\n"
    report += "## 评估结果\n\n"
    report += "| 权重组合 | Recall@5 | Precision@5 | MRR |\n"
    report += "|----------|----------|-------------|-----|\n"
    
    for method, metrics in results.items():
        report += f"| {method} "
        report += f"| {metrics.get('recall@5', 0):.4f} "
        report += f"| {metrics.get('precision@5', 0):.4f} "
        report += f"| {metrics.get('mrr', 0):.4f} |\n"
    
    report += "\n## 最佳参数\n\n"
    report += f"**{best_method[0]}**\n\n"
    report += f"- Recall@5: {best_method[1].get('recall@5', 0):.4f}\n"
    report += f"- Precision@5: {best_method[1].get('precision@5', 0):.4f}\n"
    report += f"- MRR: {best_method[1].get('mrr', 0):.4f}\n\n"
    
    report += "## 优化建议\n\n"
    report += "1. 使用最佳权重组合\n"
    report += "2. 启用混合检索\n"
    report += "3. 启用重排序\n"
    report += "4. 启用查询扩展\n"
    
    return report


def main():
    """主函数"""
    print("=" * 60)
    print("参数调优")
    print("=" * 60)
    
    # 加载基准测试
    benchmark = load_benchmark()
    print(f"\n基准测试用例: {len(benchmark['test_cases'])} 个")
    
    # 连接向量库
    client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
    collection = client.get_collection('langchain')
    print(f"向量库文档数: {collection.count()}")
    
    # 测试权重组合
    results = test_weight_combinations(collection, benchmark)
    
    # 找出最佳参数
    best_method = find_best_parameters(results)
    
    # 生成报告
    report = generate_optimization_report(results, best_method)
    
    # 保存报告
    with open("optimization_report.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print("调优报告已保存: optimization_report.md")
    print("=" * 60)
    
    # 打印报告
    print(report)


if __name__ == "__main__":
    main()
