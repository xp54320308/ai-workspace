"""
收集更多测试数据

功能：
1. 从向量库中提取更多查询
2. 自动标注相关文档
3. 扩展基准测试数据集
"""

import json
import sys
sys.path.insert(0, '.')

import chromadb
import requests


def get_embedding(text):
    """获取 embedding"""
    resp = requests.post(
        'http://localhost:11434/api/embeddings',
        json={'model': 'nomic-embed-text', 'prompt': text},
        timeout=30
    )
    return resp.json()['embedding']


def search_documents(query, collection, n_results=10):
    """搜索文档"""
    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['documents', 'metadatas']
    )
    return results


def is_relevant(query, doc_content):
    """判断文档是否相关"""
    query_lower = query.lower()
    doc_lower = doc_content.lower()
    
    # 提取查询关键词
    keywords = query_lower.split()
    
    # 检查关键词出现次数
    match_count = sum(1 for kw in keywords if kw in doc_lower)
    
    # 至少匹配一半关键词
    return match_count >= len(keywords) / 2


def collect_test_data():
    """收集测试数据"""
    print("=" * 60)
    print("收集测试数据")
    print("=" * 60)
    
    # 连接向量库
    client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
    collection = client.get_collection('langchain')
    
    print(f"\n向量库文档数: {collection.count()}")
    
    # 加载现有基准测试
    with open('benchmark.json', 'r', encoding='utf-8') as f:
        benchmark = json.load(f)
    
    existing_queries = {case['query'] for case in benchmark['test_cases']}
    print(f"现有测试用例: {len(existing_queries)} 个")
    
    # 新增测试查询
    new_queries = [
        "合同条款有哪些",
        "安全生产要求",
        "质量标准",
        "付款方式",
        "违约责任",
        "争议解决",
        "工程范围",
        "技术要求",
        "验收标准",
        "保修期限",
    ]
    
    # 收集新测试用例
    for query in new_queries:
        if query in existing_queries:
            print(f"\n跳过已存在: {query}")
            continue
        
        print(f"\n处理查询: {query}")
        
        # 搜索文档
        results = search_documents(query, collection, n_results=10)
        
        # 标注相关文档
        relevant_ids = []
        relevance_levels = {}
        
        for i, (doc, meta, doc_id) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['ids'][0]
        )):
            if is_relevant(query, doc):
                relevant_ids.append(doc_id)
                relevance_levels[doc_id] = 2
                print(f"  [{i+1}] 相关: {doc[:60]}...")
        
        if relevant_ids:
            benchmark['test_cases'].append({
                'query': query,
                'relevant_ids': relevant_ids[:5],  # 限制数量
                'relevance_levels': {k: v for k, v in list(relevance_levels.items())[:5]},
                'description': f'查询{query}'
            })
            print(f"  添加了 {len(relevant_ids)} 个相关文档")
        else:
            print(f"  未找到相关文档")
    
    # 保存更新后的基准测试
    with open('benchmark.json', 'w', encoding='utf-8') as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)
    
    print(f"\n更新后测试用例数: {len(benchmark['test_cases'])}")
    print("✅ 测试数据收集完成")


if __name__ == "__main__":
    collect_test_data()
