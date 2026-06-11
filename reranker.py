"""
重排序器

功能：
1. 使用 Cross-Encoder 重排序（如果 sentence-transformers 可用）
2. 简单规则重排序（备选方案）
"""

from typing import List, Tuple, Optional
from langchain_core.documents import Document


class SimpleReranker:
    """简单规则重排序器"""
    
    def __init__(self):
        # 关键词权重
        self.keyword_weights = {
            "contract": {"合同", "条款", "签约", "甲方", "乙方", "金额", "工期"},
            "design": {"设计", "方案", "图纸", "规范", "技术"},
            "bid": {"投标", "招标", "标书", "评标", "中标"},
        }
    
    def _compute_keyword_score(self, query: str, doc: Document) -> float:
        """计算关键词匹配分数"""
        content = doc.page_content.lower()
        query_lower = query.lower()
        
        # 查询词在文档中的出现次数
        query_words = set(query_lower.split())
        word_count = sum(1 for word in query_words if word in content)
        
        # 文档类型匹配
        doc_type = doc.metadata.get("doc_type", "general")
        type_bonus = 0
        
        for type_name, keywords in self.keyword_weights.items():
            if doc_type == type_name:
                # 检查查询是否包含该类型的关键词
                for keyword in keywords:
                    if keyword in query_lower:
                        type_bonus += 0.2
                        break
        
        # 文档长度惩罚（避免过长文档）
        length_penalty = 1.0 / (1 + len(doc.page_content) / 1000)
        
        return word_count * 0.1 + type_bonus + length_penalty * 0.1
    
    def rerank(self, query: str, documents: List[Document], 
              top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回结果数量
        
        Returns:
            (Document, score) 列表
        """
        scored_docs = []
        
        for doc in documents:
            score = self._compute_keyword_score(query, doc)
            scored_docs.append((doc, score))
        
        # 按分数降序排序
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:top_k]
    
    def invoke(self, query: str, documents: List[Document]) -> List[Document]:
        """LangChain 兼容接口"""
        results = self.rerank(query, documents, top_k=len(documents))
        return [doc for doc, score in results]


class CrossEncoderReranker:
    """Cross-Encoder 重排序器（需要 sentence-transformers）"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Args:
            model_name: Cross-Encoder 模型名称
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            print(f"✅ Cross-Encoder 模型加载成功: {self.model_name}")
        except ImportError:
            print("⚠️ sentence-transformers 未安装，使用简单重排序器")
            self.model = None
        except Exception as e:
            print(f"⚠️ Cross-Encoder 模型加载失败: {e}")
            self.model = None
    
    def rerank(self, query: str, documents: List[Document],
              top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        重排序文档
        
        Args:
            query: 查询文本
            documents: 文档列表
            top_k: 返回结果数量
        
        Returns:
            (Document, score) 列表
        """
        if not self.model or not documents:
            # 回退到简单重排序
            simple_reranker = SimpleReranker()
            return simple_reranker.rerank(query, documents, top_k)
        
        # 构建查询-文档对
        pairs = [(query, doc.page_content[:512]) for doc in documents]
        
        # 预测分数
        scores = self.model.predict(pairs)
        
        # 组合并排序
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:top_k]
    
    def invoke(self, query: str, documents: List[Document]) -> List[Document]:
        """LangChain 兼容接口"""
        results = self.rerank(query, documents, top_k=len(documents))
        return [doc for doc, score in results]


class RerankerFactory:
    """重排序器工厂"""
    
    @staticmethod
    def create(use_cross_encoder: bool = False, 
              model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        创建重排序器
        
        Args:
            use_cross_encoder: 是否使用 Cross-Encoder
            model_name: Cross-Encoder 模型名称
        
        Returns:
            重排序器实例
        """
        if use_cross_encoder:
            return CrossEncoderReranker(model_name)
        else:
            return SimpleReranker()


if __name__ == "__main__":
    # 测试
    print("=== 重排序器测试 ===")
    
    test_docs = [
        Document(page_content="合同价约7.798亿元，工期1643天，固定单价合同", 
                metadata={"doc_type": "contract", "source": "contract.pdf"}),
        Document(page_content="初步设计报告，包括船闸设计方案和技术规范", 
                metadata={"doc_type": "design", "source": "design.pdf"}),
        Document(page_content="投标文件，组织架构和评标标准", 
                metadata={"doc_type": "bid", "source": "bid.pdf"}),
        Document(page_content="Docker 容器化技术指南", 
                metadata={"doc_type": "manual", "source": "docker.txt"}),
    ]
    
    # 测试简单重排序
    reranker = SimpleReranker()
    
    queries = ["合同价", "设计方案", "Docker 容器"]
    for query in queries:
        print(f"\n查询: {query}")
        results = reranker.rerank(query, test_docs, top_k=2)
        for doc, score in results:
            print(f"  [{score:.4f}] {doc.page_content[:50]}...")
    
    print("\n✅ 重排序器测试完成")
