"""
高级检索管道

功能：
1. 混合检索（向量 + BM25）
2. 查询扩展
3. 重排序
4. 统一接口
"""

from typing import List, Dict, Optional, Tuple
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from bm25_retriever import BM25Retriever
from hybrid_retriever import HybridRetriever
from reranker import SimpleReranker, CrossEncoderReranker, RerankerFactory
from query_expander import SimpleQueryExpander, QueryExpander


class AdvancedRetriever:
    """高级检索管道"""
    
    def __init__(self,
                 persist_dir: str,
                 embedding_model: str = "nomic-embed-text",
                 vector_weight: float = 0.6,
                 bm25_weight: float = 0.4,
                 use_query_expansion: bool = True,
                 use_reranker: bool = True,
                 use_cross_encoder: bool = False,
                 top_k: int = 5):
        """
        Args:
            persist_dir: 向量库路径
            embedding_model: 嵌入模型名称
            vector_weight: 向量检索权重
            bm25_weight: BM25 检索权重
            use_query_expansion: 是否使用查询扩展
            use_reranker: 是否使用重排序
            use_cross_encoder: 是否使用 Cross-Encoder 重排序
            top_k: 返回结果数量
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.use_query_expansion = use_query_expansion
        self.use_reranker = use_reranker
        self.use_cross_encoder = use_cross_encoder
        self.top_k = top_k
        
        # 初始化组件
        self.vectorstore = None
        self.hybrid_retriever = None
        self.reranker = None
        self.query_expander = None
        
        self._init_components()
    
    def _init_components(self):
        """初始化所有组件"""
        print("🔧 初始化高级检索管道...")
        
        # 1. 初始化向量库
        embeddings = OllamaEmbeddings(model=self.embedding_model)
        self.vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=embeddings
        )
        print(f"  ✅ 向量库加载成功")
        
        # 2. 获取所有文档（用于 BM25 索引）
        try:
            collection = self.vectorstore._collection
            all_docs = collection.get(include=["documents", "metadatas"])
            
            documents = []
            for i, (doc, meta) in enumerate(zip(all_docs["documents"], all_docs["metadatas"])):
                documents.append(Document(
                    page_content=doc,
                    metadata=meta or {}
                ))
            
            print(f"  ✅ 加载 {len(documents)} 个文档用于 BM25 索引")
        except Exception as e:
            print(f"  ⚠️ 加载文档失败: {e}")
            documents = []
        
        # 3. 初始化混合检索器
        self.hybrid_retriever = HybridRetriever(
            vectorstore=self.vectorstore,
            documents=documents,
            vector_weight=self.vector_weight,
            bm25_weight=self.bm25_weight
        )
        print(f"  ✅ 混合检索器初始化完成")
        
        # 4. 初始化重排序器
        if self.use_reranker:
            self.reranker = RerankerFactory.create(
                use_cross_encoder=self.use_cross_encoder
            )
            print(f"  ✅ 重排序器初始化完成")
        
        # 5. 初始化查询扩展器
        if self.use_query_expansion:
            self.query_expander = SimpleQueryExpander()
            print(f"  ✅ 查询扩展器初始化完成")
        
        print("✅ 高级检索管道初始化完成\n")
    
    def search(self, query: str, top_k: int = None,
              filter_dict: Dict = None) -> List[Tuple[Document, float]]:
        """
        高级检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            (Document, score) 列表
        """
        top_k = top_k or self.top_k
        
        # 1. 查询扩展
        if self.use_query_expansion and self.query_expander:
            expanded_queries = self.query_expander.expand(query)
        else:
            expanded_queries = [query]
        
        # 2. 混合检索
        all_results = []
        seen_contents = set()
        
        for q in expanded_queries:
            results = self.hybrid_retriever.search(
                q, top_k=top_k * 2, filter_dict=filter_dict
            )
            
            for doc, score in results:
                content_key = doc.page_content[:100]
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    all_results.append((doc, score))
        
        # 3. 重排序
        if self.use_reranker and self.reranker:
            docs = [doc for doc, score in all_results]
            reranked = self.reranker.rerank(query, docs, top_k=top_k)
            return reranked
        else:
            # 按分数排序
            all_results.sort(key=lambda x: x[1], reverse=True)
            return all_results[:top_k]
    
    def invoke(self, query: str, config=None) -> List[Document]:
        """LangChain 兼容接口"""
        results = self.search(query)
        return [doc for doc, score in results]
    
    def search_with_context(self, query: str, top_k: int = None,
                           filter_dict: Dict = None) -> Dict:
        """
        检索并返回上下文信息
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            包含文档、分数、来源的字典
        """
        results = self.search(query, top_k, filter_dict)
        
        documents = []
        sources = set()
        
        for doc, score in results:
            documents.append(doc)
            source = doc.metadata.get("source_file", "unknown")
            sources.add(source)
        
        return {
            "query": query,
            "documents": documents,
            "sources": list(sources),
            "count": len(documents)
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "persist_dir": self.persist_dir,
            "embedding_model": self.embedding_model,
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "use_query_expansion": self.use_query_expansion,
            "use_reranker": self.use_reranker,
            "use_cross_encoder": self.use_cross_encoder,
            "top_k": self.top_k,
            "hybrid_stats": self.hybrid_retriever.get_stats() if self.hybrid_retriever else None
        }


class RetrieverFactory:
    """检索器工厂"""
    
    @staticmethod
    def create_simple(persist_dir: str, embedding_model: str = "nomic-embed-text",
                     top_k: int = 5):
        """创建简单向量检索器"""
        embeddings = OllamaEmbeddings(model=embedding_model)
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embeddings
        )
        return vectorstore.as_retriever(search_kwargs={"k": top_k})
    
    @staticmethod
    def create_hybrid(persist_dir: str, embedding_model: str = "nomic-embed-text",
                     vector_weight: float = 0.6, bm25_weight: float = 0.4,
                     top_k: int = 5):
        """创建混合检索器"""
        return AdvancedRetriever(
            persist_dir=persist_dir,
            embedding_model=embedding_model,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            use_query_expansion=False,
            use_reranker=False,
            top_k=top_k
        )
    
    @staticmethod
    def create_advanced(persist_dir: str, embedding_model: str = "nomic-embed-text",
                       vector_weight: float = 0.6, bm25_weight: float = 0.4,
                       use_query_expansion: bool = True, use_reranker: bool = True,
                       top_k: int = 5):
        """创建高级检索器"""
        return AdvancedRetriever(
            persist_dir=persist_dir,
            embedding_model=embedding_model,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            use_query_expansion=use_query_expansion,
            use_reranker=use_reranker,
            top_k=top_k
        )


if __name__ == "__main__":
    # 测试
    print("=== 高级检索管道测试 ===")
    
    # 测试同义词扩展
    expander = SimpleQueryExpander()
    test_queries = ["合同价格", "设计方案", "工期安排"]
    
    for query in test_queries:
        expanded = expander.expand(query)
        print(f"\n原始查询: {query}")
        print(f"扩展结果: {expanded}")
    
    print("\n✅ 高级检索管道测试完成")
