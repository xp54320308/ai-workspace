"""
统一评估管道

功能：
1. 对比不同检索策略
2. 生成评估报告
3. 自动化测试
"""

import json
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from retrieval_evaluator import RetrievalEvaluator, BenchmarkDataset, GroundTruth
from advanced_retriever import AdvancedRetriever, RetrieverFactory


class EvaluationPipeline:
    """统一评估管道"""
    
    def __init__(self, persist_dir, embedding_model="nomic-embed-text",
                 output_dir="eval_results"):
        """
        Args:
            persist_dir: 向量库路径
            embedding_model: 嵌入模型
            output_dir: 评估结果输出目录
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化向量库
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
        
        # 评估器
        self.evaluator = RetrievalEvaluator(output_dir=str(output_dir))
    
    def create_retriever(self, method="simple", **kwargs):
        """
        创建检索器
        
        Args:
            method: 检索方法 (simple, hybrid, advanced)
            **kwargs: 额外参数
        
        Returns:
            检索器实例
        """
        if method == "simple":
            return RetrieverFactory.create_simple(
                self.persist_dir, self.embedding_model, kwargs.get("top_k", 5)
            )
        elif method == "hybrid":
            return RetrieverFactory.create_hybrid(
                self.persist_dir, self.embedding_model,
                kwargs.get("vector_weight", 0.6),
                kwargs.get("bm25_weight", 0.4),
                kwargs.get("top_k", 5)
            )
        elif method == "advanced":
            return RetrieverFactory.create_advanced(
                self.persist_dir, self.embedding_model,
                kwargs.get("vector_weight", 0.6),
                kwargs.get("bm25_weight", 0.4),
                kwargs.get("use_query_expansion", True),
                kwargs.get("use_reranker", True),
                kwargs.get("top_k", 5)
            )
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def evaluate_method(self, method, benchmark, **kwargs):
        """
        评估单个检索方法
        
        Args:
            method: 检索方法名称
            benchmark: 基准测试数据集
            **kwargs: 额外参数
        
        Returns:
            评估指标
        """
        print(f"\n评估方法: {method}")
        
        retriever = self.create_retriever(method, **kwargs)
        test_cases = []
        
        for query, ground_truth in benchmark:
            # 执行检索
            start_time = time.time()
            
            if hasattr(retriever, 'invoke'):
                docs = retriever.invoke(query)
            else:
                docs = retriever.get_relevant_documents(query)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # 提取文档 ID
            retrieved_ids = [doc.metadata.get("id", str(i)) for i, doc in enumerate(docs)]
            
            test_cases.append((query, retrieved_ids, ground_truth))
        
        # 评估
        metrics = self.evaluator.evaluate_batch(test_cases, method=method)
        metrics["method"] = method
        
        return metrics
    
    def compare_methods(self, benchmark, methods=None, **kwargs):
        """
        对比多个检索方法
        
        Args:
            benchmark: 基准测试数据集
            methods: 方法列表
            **kwargs: 额外参数
        
        Returns:
            对比结果
        """
        if methods is None:
            methods = ["simple", "hybrid", "advanced"]
        
        results = {}
        
        for method in methods:
            try:
                metrics = self.evaluate_method(method, benchmark, **kwargs)
                results[method] = metrics
            except Exception as e:
                print(f"评估 {method} 失败: {e}")
        
        return results
    
    def generate_report(self, results):
        """
        生成评估报告
        
        Args:
            results: 评估结果
        
        Returns:
            Markdown 格式的报告
        """
        report = "# 检索方法对比报告\n\n"
        report += f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += f"**向量库**: {self.persist_dir}\n\n"
        
        # 表格
        report += "## 评估指标\n\n"
        report += "| 方法 | Recall@5 | Precision@5 | MRR | MAP | 延迟(ms) |\n"
        report += "|------|----------|-------------|-----|-----|----------|\n"
        
        for method, metrics in results.items():
            report += f"| {method} "
            report += f"| {metrics.get('recall@5', 0):.4f} "
            report += f"| {metrics.get('precision@5', 0):.4f} "
            report += f"| {metrics.get('mrr', 0):.4f} "
            report += f"| {metrics.get('map', 0):.4f} "
            report += f"| {metrics.get('latency_ms', 0):.2f} |\n"
        
        report += "\n"
        
        # 最佳方法
        best_method = max(results.items(), key=lambda x: x[1].get('mrr', 0))
        report += f"## 最佳方法\n\n"
        report += f"**{best_method[0]}** 在 MRR 指标上表现最佳 ({best_method[1].get('mrr', 0):.4f})\n"
        
        return report
    
    def save_report(self, report, filename=None):
        """保存报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_report_{timestamp}.md"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"报告已保存: {filepath}")
        return str(filepath)
    
    def run_full_evaluation(self, benchmark, methods=None, **kwargs):
        """
        运行完整评估
        
        Args:
            benchmark: 基准测试数据集
            methods: 方法列表
            **kwargs: 额外参数
        
        Returns:
            评估结果
        """
        print("=" * 60)
        print("开始完整评估")
        print("=" * 60)
        
        # 对比方法
        results = self.compare_methods(benchmark, methods, **kwargs)
        
        # 生成报告
        report = self.generate_report(results)
        
        # 保存报告
        self.save_report(report)
        
        # 保存原始结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.output_dir / f"eval_results_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n评估完成！结果已保存到: {self.output_dir}")
        
        return results


def create_sample_benchmark():
    """创建示例基准测试数据集"""
    benchmark = BenchmarkDataset()
    
    # 添加测试用例
    benchmark.add_case(
        query="合同价格",
        relevant_ids=["contract_1", "contract_2"],
        relevance_levels={"contract_1": 3, "contract_2": 2, "other_1": 0}
    )
    
    benchmark.add_case(
        query="设计方案",
        relevant_ids=["design_1", "design_2"],
        relevance_levels={"design_1": 3, "design_2": 2, "other_1": 0}
    )
    
    benchmark.add_case(
        query="投标文件",
        relevant_ids=["bid_1"],
        relevance_levels={"bid_1": 3, "other_1": 0}
    )
    
    return benchmark


if __name__ == "__main__":
    print("=== 评估管道测试 ===")
    
    # 创建基准测试
    benchmark = create_sample_benchmark()
    
    print(f"基准测试用例: {len(benchmark)} 个")
    
    # 注意：实际运行需要向量库
    # pipeline = EvaluationPipeline(persist_dir="/mnt/f/RAG_Project/chroma_db")
    # results = pipeline.run_full_evaluation(benchmark)
    
    print("\n✅ 测试完成")
