#!/usr/bin/env python3
"""
RAG 管道 v2 - 启用高级检索

用法:
  python run_rag_v2.py chat       # 启动聊天机器人 (高级检索)
  python run_rag_v2.py test       # 测试高级检索
  python run_rag_v2.py compare    # 对比普通检索和高级检索
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_chat():
    """启动聊天机器人"""
    from rag_chat_bot_v2 import run_rag_chatbot
    run_rag_chatbot()


def cmd_test():
    """测试高级检索"""
    from config import load_config
    from advanced_retriever import AdvancedRetriever
    
    config = load_config()
    
    print("=" * 60)
    print("测试高级检索器")
    print("=" * 60)
    
    # 创建高级检索器
    retriever = AdvancedRetriever(
        persist_dir=config["paths"]["persist_dir"],
        embedding_model=config["models"]["embedding"],
        vector_weight=0.6,
        bm25_weight=0.4,
        use_query_expansion=True,
        use_reranker=True,
        top_k=5
    )
    
    # 测试查询
    test_queries = [
        "合同价格是多少",
        "工期是多少天",
        "设计方案",
        "投标文件要求",
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        results = retriever.search(query, top_k=3)
        
        for i, (doc, score) in enumerate(results):
            source = doc.metadata.get("source_file", "unknown")
            print(f"  [{i+1}] score={score:.4f} source={source}")
            print(f"      {doc.page_content[:80]}...")
    
    print("\n✅ 测试完成")


def cmd_compare():
    """对比普通检索和高级检索"""
    from config import load_config
    from langchain_ollama import OllamaEmbeddings
    from langchain_chroma import Chroma
    from advanced_retriever import AdvancedRetriever
    import time
    
    config = load_config()
    persist_dir = config["paths"]["persist_dir"]
    embedding_model = config["models"]["embedding"]
    
    print("=" * 60)
    print("对比普通检索和高级检索")
    print("=" * 60)
    
    # 创建普通检索器
    embeddings = OllamaEmbeddings(model=embedding_model)
    vectorstore = Chroma(persist_directory=persist_dir, embedding_function=embeddings)
    simple_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    # 创建高级检索器
    advanced_retriever = AdvancedRetriever(
        persist_dir=persist_dir,
        embedding_model=embedding_model,
        vector_weight=0.6,
        bm25_weight=0.4,
        use_query_expansion=True,
        use_reranker=True,
        top_k=5
    )
    
    # 测试查询
    test_queries = [
        "合同价格是多少",
        "工期是多少天",
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)
        
        # 普通检索
        start = time.time()
        simple_docs = simple_retriever.invoke(query)
        simple_time = (time.time() - start) * 1000
        
        print(f"\n普通检索 ({simple_time:.0f}ms):")
        for i, doc in enumerate(simple_docs[:3]):
            source = doc.metadata.get("source_file", "unknown")
            print(f"  [{i+1}] {source}: {doc.page_content[:60]}...")
        
        # 高级检索
        start = time.time()
        advanced_docs = advanced_retriever.invoke(query)
        advanced_time = (time.time() - start) * 1000
        
        print(f"\n高级检索 ({advanced_time:.0f}ms):")
        for i, doc in enumerate(advanced_docs[:3]):
            source = doc.metadata.get("source_file", "unknown")
            print(f"  [{i+1}] {source}: {doc.page_content[:60]}...")
    
    print("\n✅ 对比完成")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == "chat":
        cmd_chat()
    elif cmd == "test":
        cmd_test()
    elif cmd == "compare":
        cmd_compare()
    else:
        print(f"❌ 未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
