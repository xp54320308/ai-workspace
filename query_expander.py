"""
查询扩展器

功能：
1. 同义词扩展
2. LLM 查询扩展（如果可用）
3. 查询改写
"""

import re
from typing import List, Dict, Set, Optional
from langchain_core.documents import Document


# 中文同义词词典
SYNONYM_DICT = {
    "合同": ["协议", "合约", "契约"],
    "价格": ["报价", "费用", "成本", "金额"],
    "设计": ["规划", "方案", "图纸"],
    "施工": ["建造", "建设", "工程"],
    "投标": ["招标", "竞标", "报价"],
    "工期": ["时间", "期限", "进度"],
    "质量": ["品质", "标准", "要求"],
    "技术": ["工艺", "方法", "方案"],
    "管理": ["管控", "监督", "协调"],
    "安全": ["防护", "保障", "措施"],
    "contract": ["agreement", "deal", "pact"],
    "price": ["cost", "fee", "expense"],
    "design": ["plan", "blueprint", "scheme"],
    "construction": ["building", "engineering", "project"],
    "bid": ["tender", "proposal", "quote"],
    "schedule": ["timeline", "deadline", "duration"],
    "quality": ["standard", "requirement", "specification"],
    "technology": ["technique", "method", "approach"],
    "management": ["supervision", "coordination", "control"],
    "safety": ["protection", "security", "measure"],
}


class QueryExpander:
    """查询扩展器"""
    
    def __init__(self, use_llm: bool = False, llm=None):
        """
        Args:
            use_llm: 是否使用 LLM 扩展
            llm: LLM 实例（用于查询扩展）
        """
        self.use_llm = use_llm
        self.llm = llm
        self.synonym_dict = SYNONYM_DICT
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词"""
        # 中文词汇
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,}', query)
        # 英文词汇
        en_words = re.findall(r'[a-zA-Z]{3,}', query.lower())
        
        return cn_words + en_words
    
    def _expand_with_synonyms(self, query: str) -> List[str]:
        """同义词扩展"""
        keywords = self._extract_keywords(query)
        expanded = [query]
        
        for keyword in keywords:
            if keyword in self.synonym_dict:
                synonyms = self.synonym_dict[keyword]
                for synonym in synonyms:
                    # 替换关键词为同义词
                    new_query = query.replace(keyword, synonym)
                    if new_query != query:
                        expanded.append(new_query)
        
        return expanded
    
    def _expand_with_llm(self, query: str, n: int = 3) -> List[str]:
        """LLM 查询扩展"""
        if not self.llm:
            return [query]
        
        try:
            prompt = f"""将以下查询扩展为 {n} 个不同表述，用于向量检索。
保持原意，但使用不同的词汇和句式。

原始查询：{query}

请直接输出 {n} 个查询，每行一个，不要编号："""
            
            response = self.llm.invoke(prompt)
            expanded = [line.strip() for line in response.content.split('\n') if line.strip()]
            
            # 添加原始查询
            expanded.insert(0, query)
            
            return expanded[:n + 1]
        except Exception as e:
            print(f"⚠️ LLM 查询扩展失败: {e}")
            return [query]
    
    def expand(self, query: str, method: str = "synonym") -> List[str]:
        """
        扩展查询
        
        Args:
            query: 原始查询
            method: 扩展方法 ("synonym", "llm", "both")
        
        Returns:
            扩展后的查询列表
        """
        if method == "synonym":
            return self._expand_with_synonyms(query)
        elif method == "llm":
            return self._expand_with_llm(query)
        elif method == "both":
            synonym_queries = self._expand_with_synonyms(query)
            llm_queries = self._expand_with_llm(query)
            
            # 合并去重
            all_queries = synonym_queries + llm_queries
            seen = set()
            unique_queries = []
            for q in all_queries:
                if q not in seen:
                    seen.add(q)
                    unique_queries.append(q)
            
            return unique_queries
        else:
            return [query]
    
    def expand_and_search(self, query: str, retriever, method: str = "synonym",
                         k: int = 5) -> List[Document]:
        """
        扩展查询并搜索
        
        Args:
            query: 原始查询
            retriever: 检索器
            method: 扩展方法
            k: 每个查询返回的结果数量
        
        Returns:
            去重后的文档列表
        """
        expanded_queries = self.expand(query, method)
        
        all_docs = []
        seen_contents = set()
        
        for q in expanded_queries:
            docs = retriever.invoke(q)
            for doc in docs:
                # 使用内容前100字符作为去重键
                content_key = doc.page_content[:100]
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    all_docs.append(doc)
        
        return all_docs[:k * 2]  # 返回最多 2k 个结果


class SimpleQueryExpander:
    """简单查询扩展器（无需 LLM）"""
    
    def __init__(self):
        self.synonym_dict = SYNONYM_DICT
    
    def expand(self, query: str) -> List[str]:
        """扩展查询"""
        keywords = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query.lower())
        expanded = [query]
        
        for keyword in keywords:
            if keyword in self.synonym_dict:
                synonyms = self.synonym_dict[keyword]
                for synonym in synonyms:
                    new_query = query.replace(keyword, synonym)
                    if new_query != query and new_query not in expanded:
                        expanded.append(new_query)
        
        return expanded


if __name__ == "__main__":
    # 测试
    print("=== 查询扩展器测试 ===")
    
    expander = SimpleQueryExpander()
    
    test_queries = [
        "合同价格",
        "设计方案",
        "投标文件",
        "工期安排",
    ]
    
    for query in test_queries:
        print(f"\n原始查询: {query}")
        expanded = expander.expand(query)
        print(f"扩展结果: {expanded}")
    
    print("\n✅ 查询扩展器测试完成")
