"""
LLM 查询扩展器

功能：
1. 使用 LLM 扩展查询
2. 查询改写
3. 多语言支持
"""

import re
from typing import List, Dict, Optional
from langchain_core.documents import Document


class LLMQueryExpander:
    """LLM 查询扩展器"""
    
    def __init__(self, llm=None, model_name="gemma4:26b", base_url="http://localhost:11434"):
        """
        Args:
            llm: LLM 实例
            model_name: 模型名称
            base_url: Ollama 服务地址
        """
        self.llm = llm
        self.model_name = model_name
        self.base_url = base_url
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM"""
        if self.llm:
            return
        
        try:
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                model=self.model_name,
                base_url=self.base_url,
                temperature=0.7
            )
            print(f"LLM 初始化成功: {self.model_name}")
        except Exception as e:
            print(f"LLM 初始化失败: {e}")
            self.llm = None
    
    def expand_query(self, query, n=3, method="diverse"):
        """
        扩展查询
        
        Args:
            query: 原始查询
            n: 扩展数量
            method: 扩展方法 (diverse, paraphrase, hyde)
        
        Returns:
            扩展后的查询列表
        """
        if not self.llm:
            return [query]
        
        if method == "diverse":
            return self._expand_diverse(query, n)
        elif method == "paraphrase":
            return self._expand_paraphrase(query, n)
        elif method == "hyde":
            return self._expand_hyde(query)
        else:
            return [query]
    
    def _expand_diverse(self, query, n):
        """多样化扩展"""
        prompt = f"""请将以下查询扩展为 {n} 个不同表述，用于向量检索。
保持原意，但使用不同的词汇和句式。
每个查询单独一行，不要编号。

原始查询：{query}

扩展查询："""
        
        try:
            response = self.llm.invoke(prompt)
            expanded = [line.strip() for line in response.content.split('\n') if line.strip()]
            expanded.insert(0, query)
            return expanded[:n + 1]
        except Exception as e:
            print(f"查询扩展失败: {e}")
            return [query]
    
    def _expand_paraphrase(self, query, n):
        """改写扩展"""
        prompt = f"""请用不同的方式改写以下查询，生成 {n} 个版本。
保持原意，但改变表达方式。
每个版本单独一行。

原始查询：{query}

改写版本："""
        
        try:
            response = self.llm.invoke(prompt)
            expanded = [line.strip() for line in response.content.split('\n') if line.strip()]
            expanded.insert(0, query)
            return expanded[:n + 1]
        except Exception as e:
            print(f"查询改写失败: {e}")
            return [query]
    
    def _expand_hyde(self, query):
        """HyDE 扩展（假设文档嵌入）"""
        prompt = f"""请根据以下查询，生成一个可能的答案片段。
这个片段应该包含查询可能涉及的关键信息。

查询：{query}

答案片段："""
        
        try:
            response = self.llm.invoke(prompt)
            hyde_text = response.content.strip()
            return [query, hyde_text]
        except Exception as e:
            print(f"HyDE 扩展失败: {e}")
            return [query]
    
    def expand_and_search(self, query, retriever, n=3, method="diverse", k=5):
        """
        扩展查询并搜索
        
        Args:
            query: 原始查询
            retriever: 检索器
            n: 扩展数量
            method: 扩展方法
            k: 每个查询返回的结果数量
        
        Returns:
            去重后的文档列表
        """
        expanded_queries = self.expand_query(query, n, method)
        
        all_docs = []
        seen_contents = set()
        
        for q in expanded_queries:
            docs = retriever.invoke(q)
            for doc in docs:
                content_key = doc.page_content[:100]
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    all_docs.append(doc)
        
        return all_docs[:k * 2]


class CachedLLMQueryExpander:
    """带缓存的 LLM 查询扩展器"""
    
    def __init__(self, llm=None, model_name="gemma4:26b",
                 base_url="http://localhost:11434", cache_dir="cache"):
        self.expander = LLMQueryExpander(llm, model_name, base_url)
        self.cache = None
        
        try:
            from cache_manager import CacheManager
            self.cache = CacheManager(cache_dir=cache_dir)
        except Exception:
            self.cache = None
    
    def expand_query(self, query, n=3, method="diverse", use_cache=True):
        """扩展查询（带缓存）"""
        # 检查缓存
        if use_cache and self.cache:
            cache_key = f"expand:{query}:{n}:{method}"
            cached = self.cache.get_query_results(cache_key, method="llm_expand")
            if cached:
                return cached
        
        # 执行扩展
        expanded = self.expander.expand_query(query, n, method)
        
        # 保存到缓存
        if use_cache and self.cache:
            self.cache.set_query_results(cache_key, expanded, method="llm_expand")
        
        return expanded


if __name__ == "__main__":
    print("=== LLM 查询扩展器测试 ===")
    
    expander = LLMQueryExpander()
    
    test_queries = [
        "合同价格",
        "设计方案",
    ]
    
    for query in test_queries:
        print(f"\n原始查询: {query}")
        
        # 测试多样化扩展
        expanded = expander.expand_query(query, n=2, method="diverse")
        print(f"多样化扩展: {expanded}")
        
        # 测试改写扩展
        paraphrased = expander.expand_query(query, n=2, method="paraphrase")
        print(f"改写扩展: {paraphrased}")
    
    print("\n✅ 测试完成")
