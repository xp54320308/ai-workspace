"""
元数据增强器

功能：
1. 文档类型分类（contract, design, spec, general）
2. 项目名称提取（fujinba, weituo）
3. 章节标题提取
4. 其他有用信息提取
"""

import os
import re
from typing import Dict, List, Optional, Any
from langchain_core.documents import Document


# 文档类型关键词映射
DOC_TYPE_PATTERNS = {
    "contract": [
        r"合同", r"协议", r"条款", r"签约", r"承包", r"发包", r"甲方", r"乙方",
        r"contract", r"agreement"
    ],
    "design": [
        r"设计", r"初步设计", r"施工图", r"图纸", r"技术规范", r"design",
        r"specification", r"drawing"
    ],
    "bid": [
        r"投标", r"招标", r"标书", r"评标", r"中标", r"bid", r"tender"
    ],
    "report": [
        r"报告", r"总结", r"汇报", r"分析", r"report", r"summary"
    ],
    "manual": [
        r"手册", r"指南", r"教程", r"说明", r"manual", r"guide", r"tutorial"
    ]
}

# 项目名称映射
PROJECT_PATTERNS = {
    "fujinba": [r"富金坝", r"金坝", r"fujinba"],
    "weituo": [r"渭沱", r"weituo"],
    "fujiang": [r"涪江", r"fujiang"]
}


class MetadataEnricher:
    """元数据增强器"""
    
    def __init__(self):
        self.doc_type_patterns = DOC_TYPE_PATTERNS
        self.project_patterns = PROJECT_PATTERNS
    
    def classify_document(self, file_path: str, content: str = "") -> str:
        """
        分类文档类型
        
        Args:
            file_path: 文件路径
            content: 文档内容（可选，用于更精确分类）
        
        Returns:
            文档类型：contract, design, bid, report, manual, general
        """
        # 从文件名提取信息
        filename = os.path.basename(file_path).lower()
        
        # 从内容提取信息（取前500字符）
        text_to_analyze = filename + " " + content[:500] if content else filename
        
        # 计算每种类型的匹配分数
        scores = {}
        for doc_type, patterns in self.doc_type_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_to_analyze, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[doc_type] = score
        
        # 返回得分最高的类型
        if scores:
            return max(scores, key=scores.get)
        return "general"
    
    def extract_project(self, file_path: str, content: str = "") -> str:
        """
        提取项目名称
        
        Args:
            file_path: 文件路径
            content: 文档内容
        
        Returns:
            项目名称：fujinba, weituo, fujiang, unknown
        """
        filename = os.path.basename(file_path).lower()
        text_to_analyze = filename + " " + content[:500] if content else filename
        
        for project, patterns in self.project_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_analyze, re.IGNORECASE):
                    return project
        return "unknown"
    
    def extract_section_title(self, content: str) -> Optional[str]:
        """
        从内容中提取章节标题
        
        Args:
            content: 文本内容
        
        Returns:
            章节标题或 None
        """
        # 匹配常见的章节标题格式
        patterns = [
            r"^第[一二三四五六七八九十\d]+[章节条款].*$",  # 第一章、第1节
            r"^#+\s+.+$",  # Markdown 标题
            r"^[一二三四五六七八九十]+[、.]\s*.+$",  # 一、二、
            r"^\d+[、.]\s*.+$",  # 1. 2.
            r"^第\d+条\s*.+$",  # 第1条
        ]
        
        for line in content.split('\n')[:20]:  # 只检查前20行
            line = line.strip()
            for pattern in patterns:
                if re.match(pattern, line):
                    # 清理标题
                    title = re.sub(r'^#+\s*', '', line)  # 去掉 Markdown 标记
                    title = title[:50]  # 限制长度
                    return title
        return None
    
    def extract_keywords(self, content: str, max_keywords: int = 10) -> List[str]:
        """
        从内容中提取关键词
        
        Args:
            content: 文本内容
            max_keywords: 最大关键词数量
        
        Returns:
            关键词列表
        """
        # 简单的关键词提取（基于词频）
        # 移除标点符号和数字
        text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', content)
        
        # 提取中文词汇（2-4字）
        cn_words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        
        # 提取英文词汇（3字以上）
        en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        
        # 统计词频
        word_freq = {}
        for word in cn_words + en_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序，返回前N个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
    
    def extract_dates(self, content: str) -> List[str]:
        """
        从内容中提取日期
        
        Args:
            content: 文本内容
        
        Returns:
            日期列表
        """
        patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 2024年1月1日
            r'\d{4}-\d{1,2}-\d{1,2}',  # 2024-01-01
            r'\d{4}/\d{1,2}/\d{1,2}',  # 2024/01/01
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            dates.extend(matches)
        
        return list(set(dates))[:5]  # 去重，最多返回5个
    
    def extract_amounts(self, content: str) -> List[str]:
        """
        从内容中提取金额
        
        Args:
            content: 文本内容
        
        Returns:
            金额列表
        """
        patterns = [
            r'[\d,]+\.?\d*万元',  # 123.45万元
            r'[\d,]+\.?\d*元',  # 123.45元
            r'[\d,]+\.?\d*亿美元',  # 1.23亿美元
            r'[\d,]+\.?\d*美元',  # 123.45美元
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            amounts.extend(matches)
        
        return list(set(amounts))[:5]  # 去重，最多返回5个
    
    def enrich_metadata(self, doc: Document, file_path: str) -> Document:
        """
        增强文档元数据
        
        Args:
            doc: LangChain Document 对象
            file_path: 文件路径
        
        Returns:
            增强后的 Document
        """
        content = doc.page_content
        
        # 基础元数据
        enriched = {
            "source": file_path,
            "source_file": os.path.basename(file_path),
            "file_extension": os.path.splitext(file_path)[1].lower(),
            "char_count": len(content),
        }
        
        # 文档类型分类
        enriched["doc_type"] = self.classify_document(file_path, content)
        
        # 项目提取
        enriched["project"] = self.extract_project(file_path, content)
        
        # 章节标题
        section = self.extract_section_title(content)
        if section:
            enriched["section"] = section
        
        # 关键词
        keywords = self.extract_keywords(content)
        if keywords:
            enriched["keywords"] = ",".join(keywords)
        
        # 日期
        dates = self.extract_dates(content)
        if dates:
            enriched["dates"] = ",".join(dates)
        
        # 金额
        amounts = self.extract_amounts(content)
        if amounts:
            enriched["amounts"] = ",".join(amounts)
        
        # 更新时间
        from datetime import datetime
        enriched["ingested_at"] = datetime.now().isoformat()
        
        # 合并到现有元数据
        doc.metadata.update(enriched)
        
        return doc
    
    def enrich_documents(self, docs: List[Document], file_path: str) -> List[Document]:
        """
        批量增强文档元数据
        
        Args:
            docs: Document 列表
            file_path: 文件路径
        
        Returns:
            增强后的 Document 列表
        """
        return [self.enrich_metadata(doc, file_path) for doc in docs]


# 便捷函数
def enrich_single_document(doc: Document, file_path: str) -> Document:
    """增强单个文档的元数据"""
    enricher = MetadataEnricher()
    return enricher.enrich_metadata(doc, file_path)


def enrich_document_list(docs: List[Document], file_path: str) -> List[Document]:
    """增强文档列表的元数据"""
    enricher = MetadataEnricher()
    return enricher.enrich_documents(docs, file_path)


if __name__ == "__main__":
    # 测试
    enricher = MetadataEnricher()
    
    test_cases = [
        ("涪江富金坝电厂船闸扩能升级改造工程施工总承包合同.docx", "合同价约7.798亿元"),
        ("渭沱电厂初步设计.pdf", "初步设计报告"),
        ("投标组织方案.docx", "投标文件"),
    ]
    
    for filename, content in test_cases:
        doc_type = enricher.classify_document(filename, content)
        project = enricher.extract_project(filename, content)
        print(f"{filename}:")
        print(f"  类型: {doc_type}")
        print(f"  项目: {project}")
        print()
