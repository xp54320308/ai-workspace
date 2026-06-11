"""
混合检索器

功能：
1. 向量检索（语义相似度）
2. BM25 检索（关键词匹配）
3. 混合检索（加权融合）
"""

from typing import List, Dict, Tuple, Optional, Callable
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from bm25_retriever import BM25Retriever, LangChainBM25Retriever


class HybridRetriever:
    """混合检索器：向量 + BM25"""
    
    def __init__(self, 
                 vectorstore: Chroma,
                 documents: List[Document] = None,
                 vector_weight: float = 0.6,
                 bm25_weight: float = 0.4,
                 vector_k: int = 10,
                 bm25_k: int = 10):
        """
        Args:
            vectorstore: Chroma 向量库
            documents: 文档列表（用于 BM25 索引）
            vector_weight: 向量检索权重
            bm25_weight: BM25 检索权重
            vector_k: 向量检索返回数量
            bm25_k: BM25 检索返回数量
        """
        self.vectorstore = vectorstore
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.vector_k = vector_k
        self.bm25_k = bm25_k
        
        # 初始化 BM25
        self.bm25 = BM25Retriever()
        if documents:
            self.bm25.add_documents(documents)
        
        # 文档 ID 到索引的映射
        self.doc_id_to_idx: Dict[str, int] = {}
        self._build_doc_mapping()
    
    def _build_doc_mapping(self):
        """构建文档 ID 到索引的映射"""
        for i, doc in enumerate(self.bm25.documents):
            doc_id = doc.metadata.get("id", str(i))
            self.doc_id_to_idx[doc_id] = i
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """归一化分数到 [0, 1]"""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    def _vector_search(self, query: str, k: int = None, 
                      filter_dict: Dict = None) -> List[Tuple[Document, float]]:
        """向量检索"""
        k = k or self.vector_k
        
        search_kwargs = {"k": k}
        if filter_dict:
            search_kwargs["filter"] = filter_dict
        
        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        docs = retriever.invoke(query)
        
        # 向量检索不返回分数，使用排名作为分数
        results = []
        for i, doc in enumerate(docs):
            score = 1.0 - (i / len(docs)) if docs else 0
            results.append((doc, score))
        
        return results
    
    def _bm25_search(self, query: str, k: int = None,
                    filter_fn: Callable = None) -> List[Tuple[Document, float]]:
        """BM25 检索"""
        k = k or self.bm25_k
        
        if filter_fn:
            results = self.bm25.search_with_filter(query, k=k, filter_fn=filter_fn)
        else:
            results = self.bm25.search(query, k=k)
        
        return results
    
    def _merge_results(self, 
                      vector_results: List[Tuple[Document, float]],
                      bm25_results: List[Tuple[Document, float]],
                      top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        融合向量和 BM25 检索结果
        
        使用 RRF (Reciprocal Rank Fusion) 算法
        """
        # 文档 ID 到分数的映射
        doc_scores: Dict[str, Tuple[Document, float]] = {}
        
        # 处理向量检索结果
        for i, (doc, score) in enumerate(vector_results):
            doc_id = doc.metadata.get("id", id(doc))
            rrf_score = 1.0 / (60 + i)  # RRF 公式
            weighted_score = rrf_score * self.vector_weight
            
            if doc_id in doc_scores:
                existing_doc, existing_score = doc_scores[doc_id]
                doc_scores[doc_id] = (doc, existing_score + weighted_score)
            else:
                doc_scores[doc_id] = (doc, weighted_score)
        
        # 处理 BM25 检索结果
        for i, (doc, score) in enumerate(bm25_results):
            doc_id = doc.metadata.get("id", id(doc))
            rrf_score = 1.0 / (60 + i)  # RRF 公式
            weighted_score = rrf_score * self.bm25_weight
            
            if doc_id in doc_scores:
                existing_doc, existing_score = doc_scores[doc_id]
                doc_scores[doc_id] = (doc, existing_score + weighted_score)
            else:
                doc_scores[doc_id] = (doc, weighted_score)
        
        # 按分数降序排序
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def search(self, query: str, top_k: int = 5,
              filter_dict: Dict = None) -> List[Tuple[Document, float]]:
        """
        混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            (Document, score) 列表
        """
        # 向量检索
        vector_results = self._vector_search(query, filter_dict=filter_dict)
        
        # BM25 检索
        bm25_results = self._bm25_search(query)
        
        # 融合结果
        return self._merge_results(vector_results, bm25_results, top_k)
    
    def invoke(self, query: str, config=None) -> List[Document]:
        """LangChain 兼容接口"""
        results = self.search(query, top_k=5)
        return [doc for doc, score in results]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "bm25_stats": self.bm25.get_stats()
        }


class HybridRetrieverV2:
    """混合检索器 V2：支持分数归一化"""
    
    def __init__(self, 
                 vectorstore: Chroma,
                 documents: List[Document] = None,
                 vector_weight: float = 0.6,
                 bm25_weight: float = 0.4):
        """
        Args:
            vectorstore: Chroma 向量库
            documents: 文档列表（用于 BM25 索引）
            vector_weight: 向量检索权重
            bm25_weight: BM25 检索权重
        """
        self.vectorstore = vectorstore
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        
        # 初始化 BM25
        self.bm25 = BM25Retriever()
        if documents:
            self.bm25.add_documents(documents)
    
    def search(self, query: str, top_k: int = 5,
              filter_dict: Dict = None) -> List[Tuple[Document, float]]:
        """
        混合检索（带分数归一化）
        """
        # 向量检索
        vector_docs = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=top_k * 2, filter=filter_dict
        )
        
        # BM25 检索
        bm25_results = self.bm25.search(query, k=top_k * 2)
        
        # 归一化分数
        vector_scores = [score for _, score in vector_docs]
        bm25_scores = [score for _, score in bm25_results]
        
        vector_scores_norm = self._normalize_scores(vector_scores)
        bm25_scores_norm = self._normalize_scores(bm25_scores)
        
        # 融合
        doc_scores: Dict[str, Tuple[Document, float]] = {}
        
        for i, (doc, _) in enumerate(vector_docs):
            doc_id = doc.metadata.get("id", id(doc))
            score = vector_scores_norm[i] * self.vector_weight
            doc_scores[doc_id] = (doc, score)
        
        for i, (doc, _) in enumerate(bm25_results):
            doc_id = doc.metadata.get("id", id(doc))
            score = bm25_scores_norm[i] * self.bm25_weight
            
            if doc_id in doc_scores:
                existing_doc, existing_score = doc_scores[doc_id]
                doc_scores[doc_id] = (doc, existing_score + score)
            else:
                doc_scores[doc_id] = (doc, score)
        
        # 排序并返回
        sorted_results = sorted(
            doc_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """归一化分数"""
        if not scores:
            return []
        
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    def invoke(self, query: str, config=None) -> List[Document]:
        """LangChain 兼容接口"""
        results = self.search(query, top_k=5)
        return [doc for doc, score in results]


if __name__ == "__main__":
    # 测试
    print("=== 混合检索器测试 ===")
    
    # 创建测试文档
    test_docs = [
        Document(page_content="合同价约7.798亿元，工期1643天", 
                metadata={"id": "1", "source": "contract.pdf", "doc_type": "contract"}),
        Document(page_content="初步设计报告，包括船闸设计方案", 
                metadata={"id": "2", "source": "design.pdf", "doc_type": "design"}),
        Document(page_content="投标文件，组织架构和评标标准", 
                metadata={"id": "3", "source": "bid.pdf", "doc_type": "bid"}),
        Document(page_content="Docker 容器化技术指南", 
                metadata={"id": "4", "source": "docker.txt", "doc_type": "manual"}),
    ]
    
    # 测试 BM25
    bm25 = BM25Retriever()
    bm25.add_documents(test_docs)
    
    print("\nBM25 检索测试:")
    results = bm25.search("合同价", k=2)
    for doc, score in results:
        print(f"  [{score:.4f}] {doc.page_content[:50]}...")
    
    print("\n✅ 混合检索器测试完成")
