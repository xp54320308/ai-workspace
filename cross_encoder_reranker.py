"""
Cross-Encoder 重排序器

功能：
1. 使用 Cross-Encoder 模型重排序
2. 支持多种模型
3. 批量处理优化
"""

import os
from typing import List, Dict, Tuple, Optional
from langchain_core.documents import Document


class CrossEncoderReranker:
    """Cross-Encoder 重排序器"""
    
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2", device=None):
        """
        Args:
            model_name: Cross-Encoder 模型名称
            device: 设备 (cpu/cuda)
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, device=self.device)
            print(f"Cross-Encoder 模型加载成功: {self.model_name}")
        except ImportError:
            print("sentence-transformers 未安装，使用简单重排序")
            self.model = None
        except Exception as e:
            print(f"Cross-Encoder 模型加载失败: {e}")
            self.model = None
    
    def rerank(self, query, documents, top_k=5, max_length=512):
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回结果数量
            max_length: 最大文本长度
        
        Returns:
            (Document, score) 列表
        """
        if not self.model or not documents:
            return self._fallback_rerank(query, documents, top_k)
        
        # 构建查询-文档对
        pairs = []
        for doc in documents:
            text = doc.page_content[:max_length]
            pairs.append([query, text])
        
        # 预测分数
        scores = self.model.predict(pairs)
        
        # 组合并排序
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:top_k]
    
    def _fallback_rerank(self, query, documents, top_k):
        """简单重排序（当 Cross-Encoder 不可用时）"""
        query_lower = query.lower()
        scored_docs = []
        
        for doc in documents:
            content = doc.page_content.lower()
            # 简单的关键词匹配分数
            score = sum(1 for word in query_lower.split() if word in content)
            scored_docs.append((doc, score))
        
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:top_k]
    
    def invoke(self, query, documents):
        """LangChain 兼容接口"""
        results = self.rerank(query, documents, top_k=len(documents))
        return [doc for doc, score in results]


class CachedCrossEncoderReranker:
    """带缓存的 Cross-Encoder 重排序器"""
    
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
                 cache_dir="cache", device=None):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.cache = None
        self._load_model()
        self._init_cache(cache_dir)
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name, device=self.device)
            print(f"Cross-Encoder 模型加载成功: {self.model_name}")
        except Exception as e:
            print(f"Cross-Encoder 模型加载失败: {e}")
            self.model = None
    
    def _init_cache(self, cache_dir):
        """初始化缓存"""
        try:
            from cache_manager import CacheManager
            self.cache = CacheManager(cache_dir=cache_dir)
        except Exception:
            self.cache = None
    
    def rerank(self, query, documents, top_k=5, use_cache=True):
        """重排序文档（带缓存）"""
        # 检查缓存
        if use_cache and self.cache:
            cache_key = f"rerank:{query}:{len(documents)}"
            cached = self.cache.get_query_results(cache_key, method="cross_encoder")
            if cached:
                # 重建结果
                results = []
                for item in cached:
                    doc = Document(page_content=item["content"], metadata=item["metadata"])
                    results.append((doc, item["score"]))
                return results[:top_k]
        
        # 执行重排序
        if not self.model:
            return self._fallback_rerank(query, documents, top_k)
        
        pairs = [[query, doc.page_content[:512]] for doc in documents]
        scores = self.model.predict(pairs)
        
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        results = scored_docs[:top_k]
        
        # 保存到缓存
        if use_cache and self.cache:
            cache_data = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
                for doc, score in results
            ]
            self.cache.set_query_results(cache_key, cache_data, method="cross_encoder")
        
        return results
    
    def _fallback_rerank(self, query, documents, top_k):
        """简单重排序"""
        query_lower = query.lower()
        scored_docs = []
        
        for doc in documents:
            content = doc.page_content.lower()
            score = sum(1 for word in query_lower.split() if word in content)
            scored_docs.append((doc, score))
        
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[:top_k]


if __name__ == "__main__":
    print("=== Cross-Encoder 重排序器测试 ===")
    
    reranker = CrossEncoderReranker()
    
    test_docs = [
        Document(page_content="合同价约7.798亿元，工期1643天", metadata={"source": "contract.pdf"}),
        Document(page_content="初步设计报告，包括船闸设计方案", metadata={"source": "design.pdf"}),
        Document(page_content="投标文件，组织架构和评标标准", metadata={"source": "bid.pdf"}),
    ]
    
    results = reranker.rerank("合同价", test_docs, top_k=2)
    print(f"\n查询: 合同价")
    for doc, score in results:
        print(f"  [{score:.4f}] {doc.page_content[:50]}...")
    
    print("\n✅ 测试完成")
