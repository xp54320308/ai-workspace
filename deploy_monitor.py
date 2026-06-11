"""
部署监控脚本

功能：
1. 定期评估检索质量
2. 记录性能指标
3. 生成监控报告
"""

import json
import time
from datetime import datetime
from pathlib import Path


class RetrievalMonitor:
    """检索质量监控器"""
    
    def __init__(self, log_dir="monitor_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history = []
    
    def log_metrics(self, metrics, method="unknown"):
        """记录指标"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "metrics": metrics
        }
        self.metrics_history.append(entry)
        
        # 保存到文件
        log_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        return entry
    
    def check_threshold(self, metrics, thresholds=None):
        """检查指标是否低于阈值"""
        if thresholds is None:
            thresholds = {
                "recall@5": 0.3,
                "precision@5": 0.2,
                "mrr": 0.3
            }
        
        alerts = []
        for metric, threshold in thresholds.items():
            value = metrics.get(metric, 0)
            if value < threshold:
                alerts.append(f"{metric} = {value:.4f} < {threshold}")
        
        return alerts
    
    def generate_daily_report(self):
        """生成日报"""
        today = datetime.now().strftime('%Y%m%d')
        log_file = self.log_dir / f"metrics_{today}.json"
        
        if not log_file.exists():
            return "今日无监控数据"
        
        entries = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        if not entries:
            return "今日无监控数据"
        
        report = f"# 监控日报 {today}\n\n"
        report += f"监控次数: {len(entries)}\n\n"
        
        # 计算平均指标
        avg_metrics = {}
        for entry in entries:
            for metric, value in entry['metrics'].items():
                if metric not in avg_metrics:
                    avg_metrics[metric] = []
                avg_metrics[metric].append(value)
        
        report += "## 平均指标\n\n"
        for metric, values in avg_metrics.items():
            avg = sum(values) / len(values)
            report += f"- {metric}: {avg:.4f}\n"
        
        return report


def run_monitor():
    """运行监控"""
    monitor = RetrievalMonitor()
    
    print("=" * 60)
    print("检索质量监控")
    print("=" * 60)
    
    # 模拟监控数据
    test_metrics = {
        "recall@5": 0.35,
        "precision@5": 0.25,
        "mrr": 0.40,
        "latency_ms": 50.0
    }
    
    # 记录指标
    entry = monitor.log_metrics(test_metrics, method="vector")
    print(f"\n记录指标: {entry['timestamp']}")
    
    # 检查阈值
    alerts = monitor.check_threshold(test_metrics)
    if alerts:
        print("\n告警:")
        for alert in alerts:
            print(f"  - {alert}")
    else:
        print("\n所有指标正常")
    
    # 生成日报
    report = monitor.generate_daily_report()
    print("\n" + report)
    
    print("\n✅ 监控完成")


if __name__ == "__main__":
    run_monitor()
