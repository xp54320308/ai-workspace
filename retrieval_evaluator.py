"""
检索评估框架
"""

import json
from typing import List, Dict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class GroundTruth:
    query: str
    relevant_ids: List[str]
    relevance_levels: Dict[str, int] = None


class RetrievalMetrics:
    @staticmethod
    def recall_at_k(retrieved, relevant, k):
        if not relevant:
            return 0.0
        return len(set(retrieved[:k]) & set(relevant)) / len(set(relevant))
    
    @staticmethod
    def precision_at_k(retrieved, relevant, k):
        if k == 0:
            return 0.0
        return len(set(retrieved[:k]) & set(relevant)) / k
    
    @staticmethod
    def mrr(retrieved, relevant):
        relevant_set = set(relevant)
        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def ndcg_at_k(retrieved, relevance_levels, k):
        if not relevance_levels:
            return 0.0
        dcg = sum((2 ** relevance_levels.get(doc_id, 0) - 1) / (1 + i) for i, doc_id in enumerate(retrieved[:k]))
        ideal = sorted(relevance_levels.values(), reverse=True)[:k]
        idcg = sum((2 ** level - 1) / (1 + i) for i, level in enumerate(ideal))
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def map_score(retrieved, relevant):
        if not relevant:
            return 0.0
        relevant_set = set(relevant)
        precisions = []
        num_relevant = 0
        for i, doc_id in enumerate(retrieved):
            if doc_id in relevant_set:
                num_relevant += 1
                precisions.append(num_relevant / (i + 1))
        return sum(precisions) / len(relevant) if precisions else 0.0


class RetrievalEvaluator:
    def __init__(self, output_dir="eval_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = RetrievalMetrics()
        self.results = []
    
    def evaluate_single(self, query, retrieved_ids, ground_truth, method="unknown", latency_ms=0.0):
        relevant_ids = ground_truth.relevant_ids
        relevance_levels = ground_truth.relevance_levels or {}
        
        metrics = {
            "recall@1": self.metrics.recall_at_k(retrieved_ids, relevant_ids, 1),
            "recall@3": self.metrics.recall_at_k(retrieved_ids, relevant_ids, 3),
            "recall@5": self.metrics.recall_at_k(retrieved_ids, relevant_ids, 5),
            "precision@1": self.metrics.precision_at_k(retrieved_ids, relevant_ids, 1),
            "precision@5": self.metrics.precision_at_k(retrieved_ids, relevant_ids, 5),
            "mrr": self.metrics.mrr(retrieved_ids, relevant_ids),
            "map": self.metrics.map_score(retrieved_ids, relevant_ids),
            "latency_ms": latency_ms,
        }
        
        if relevance_levels:
            metrics["ndcg@5"] = self.metrics.ndcg_at_k(retrieved_ids, relevance_levels, 5)
        
        return metrics
    
    def evaluate_batch(self, test_cases, method="unknown"):
        all_metrics = []
        for query, retrieved_ids, ground_truth in test_cases:
            metrics = self.evaluate_single(query, retrieved_ids, ground_truth, method)
            all_metrics.append(metrics)
        
        avg_metrics = {}
        for key in all_metrics[0].keys():
            values = [m[key] for m in all_metrics]
            avg_metrics[key] = sum(values) / len(values)
        
        return avg_metrics
    
    def save_results(self, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_results_{timestamp}.json"
        
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": datetime.now().isoformat(), "results": self.results}, f, ensure_ascii=False, indent=2)
        
        print(f"评估结果已保存: {filepath}")
        return str(filepath)


class BenchmarkDataset:
    def __init__(self):
        self.test_cases = []
    
    def add_case(self, query, relevant_ids, relevance_levels=None):
        ground_truth = GroundTruth(query=query, relevant_ids=relevant_ids, relevance_levels=relevance_levels)
        self.test_cases.append((query, ground_truth))
    
    def __len__(self):
        return len(self.test_cases)
    
    def __iter__(self):
        return iter(self.test_cases)


if __name__ == "__main__":
    print("=== 测试 ===")
    benchmark = BenchmarkDataset()
    benchmark.add_case("合同价格", ["doc1", "doc2"], {"doc1": 3, "doc2": 2})
    
    evaluator = RetrievalEvaluator("/tmp/eval")
    test_cases = [("合同价格", ["doc1", "doc3", "doc2"], GroundTruth("合同价格", ["doc1", "doc2"], {"doc1": 3, "doc2": 2}))]
    
    metrics = evaluator.evaluate_batch(test_cases)
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    
    evaluator.save_results()
    print("OK")
