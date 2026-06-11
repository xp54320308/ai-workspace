"""
BM25 检索器

功能：
1. 中文分词支持
2. BM25 检索
3. 与向量检索兼容的接口
"""

import re
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter
from langchain_core.documents import Document


class ChineseTokenizer:
    """中文分词器（简单实现，无需 jieba）"""
    
    def __init__(self):
        # 常见停用词
        self.stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
            '自己', '这', '他', '她', '它', '们', '那', '些', '什么', '怎么', '如何', '为什么',
            '可以', '可能', '应该', '需要', '必须', 'shall', 'will', 'the', 'a', 'an', 'is',
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'need',
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        分词：中文按字/词切分，英文按空格切分
        
        Args:
            text: 输入文本
        
        Returns:
            token 列表
        """
        # 转小写
        text = text.lower()
        
        # 提取中文词汇（2-4字）和英文单词
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        cn_chars = re.findall(r'[\u4e00-\u9fff]', text)
        en_words = re.findall(r'[a-zA-Z]{2,}', text)
        
        # 合并并去停用词
        tokens = cn_words + cn_chars + en_words
        tokens = [t for t in tokens if t not in self.stop_words]
        
        return tokens


class BM25Retriever:
    """BM25 检索器"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: BM25 参数 k1
            b: BM25 参数 b
        """
        self.k1 = k1
        self.b = b
        self.tokenizer = ChineseTokenizer()
        
        # 文档索引
        self.documents: List[Document] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_freqs: List[Counter] = []
        self.avg_dl: float = 0
        self.corpus_size: int = 0
        self.idf: Dict[str, float] = {}
    
    def _compute_idf(self):
        """计算 IDF 值"""
        doc_count = Counter()
        
        for freq in self.doc_freqs:
            for token in freq:
                doc_count[token] += 1
        
        self.idf = {}
        for token, count in doc_count.items():
            # IDF 公式：log((N - n + 0.5) / (n + 0.5) + 1)
            self.idf[token] = math.log(
                (self.corpus_size - count + 0.5) / (count + 0.5) + 1
            )
    
    def add_documents(self, documents: List[Document]):
        """
        添加文档到索引
        
        Args:
            documents: Document 列表
        """
        for doc in documents:
            tokens = self.tokenizer.tokenize(doc.page_content)
            freq = Counter(tokens)
            
            self.documents.append(doc)
            self.doc_tokens.append(tokens)
            self.doc_freqs.append(freq)
        
        # 更新统计信息
        self.corpus_size = len(self.documents)
        total_dl = sum(len(tokens) for tokens in self.doc_tokens)
        self.avg_dl = total_dl / self.corpus_size if self.corpus_size > 0 else 0
        
        # 重新计算 IDF
        self._compute_idf()
    
    def _score_document(self, query_tokens: List[str], doc_idx: int) -> float:
        """
        计算查询与文档的相关性分数
        
        Args:
            query_tokens: 查询 token 列表
            doc_idx: 文档索引
        
        Returns:
            BM25 分数
        """
        doc_freq = self.doc_freqs[doc_idx]
        doc_len = len(self.doc_tokens[doc_idx])
        
        score = 0.0
        for token in query_tokens:
            if token not in doc_freq:
                continue
            
            tf = doc_freq[token]
            idf = self.idf.get(token, 0)
            
            # BM25 公式
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_dl)
            score += idf * numerator / denominator
        
        return score
    
    def search(self, query: str, k: int = 5) -> List[Tuple[Document, float]]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            k: 返回结果数量
        
        Returns:
            (Document, score) 列表
        """
        if not self.documents:
            return []
        
        query_tokens = self.tokenizer.tokenize(query)
        
        # 计算每个文档的分数
        scores = []
        for i in range(self.corpus_size):
            score = self._score_document(query_tokens, i)
            scores.append((i, score))
        
        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 top-k 结果
        results = []
        for idx, score in scores[:k]:
            results.append((self.documents[idx], score))
        
        return results
    
    def search_with_filter(self, query: str, k: int = 5, 
                          filter_fn=None) -> List[Tuple[Document, float]]:
        """
        带过滤的搜索
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filter_fn: 过滤函数，接受 Document，返回 bool
        
        Returns:
            (Document, score) 列表
        """
        if not self.documents:
            return []
        
        query_tokens = self.tokenizer.tokenize(query)
        
        # 计算每个文档的分数
        scores = []
        for i in range(self.corpus_size):
            if filter_fn and not filter_fn(self.documents[i]):
                continue
            score = self._score_document(query_tokens, i)
            scores.append((i, score))
        
        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 返回 top-k 结果
        results = []
        for idx, score in scores[:k]:
            results.append((self.documents[idx], score))
        
        return results
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            "corpus_size": self.corpus_size,
            "avg_doc_length": self.avg_dl,
            "vocabulary_size": len(self.idf)
        }


# LangChain 兼容接口
class LangChainBM25Retriever:
    """LangChain 兼容的 BM25 检索器"""
    
    def __init__(self, bm25: BM25Retriever, k: int = 5):
        self.bm25 = bm25
        self.k = k
    
    def invoke(self, query: str, config=None) -> List[Document]:
        """LangChain 兼容的 invoke 接口"""
        results = self.bm25.search(query, k=self.k)
        return [doc for doc, score in results]
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """旧版 LangChain 兼容接口"""
        return self.invoke(query)


if __name__ == "__main__":
    # 测试
    bm25 = BM25Retriever()
    
    test_docs = [
        Document(page_content="合同价约7.798亿元，工期1643天", metadata={"source": "contract.pdf"}),
        Document(page_content="初步设计报告，包括船闸设计方案", metadata={"source": "design.pdf"}),
        Document(page_content="投标文件，组织架构和评标标准", metadata={"source": "bid.pdf"}),
        Document(page_content="Docker 容器化技术指南", metadata={"source": "docker.txt"}),
    ]
    
    bm25.add_documents(test_docs)
    
    print("=== BM25 检索测试 ===")
    print(f"索引统计: {bm25.get_stats()}")
    
    queries = ["合同价", "设计方案", "Docker 容器"]
    for query in queries:
        print(f"\n查询: {query}")
        results = bm25.search(query, k=2)
        for doc, score in results:
            print(f"  [{score:.4f}] {doc.page_content[:50]}...")
