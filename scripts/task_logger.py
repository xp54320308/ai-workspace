"""
Task Logger — 任务日志记录与错误重试
自动记录每个 action 的输入/输出/耗时，失败时自动重试

Usage:
    from task_logger import TaskLogger
    logger = TaskLogger("workflow_name")
    logger.log("step_name", input_data, output_data, elapsed_ms)
"""

import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Optional

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class TaskLogger:
    """任务日志记录器"""
    
    def __init__(self, workflow_name: str, max_retries: int = 3):
        self.workflow_name = workflow_name
        self.max_retries = max_retries
        self.log_file = LOG_DIR / f"{workflow_name}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.current_task = None
        self.start_time = None
        
    def start_task(self, task_name: str):
        """开始一个任务"""
        self.current_task = task_name
        self.start_time = time.time()
        return self
    
    def log(self, step_name: str, input_data: Any, output: Any, elapsed_ms: float, status: str = "success"):
        """记录步骤日志"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "workflow": self.workflow_name,
            "step": step_name,
            "input": str(input_data)[:500] if input_data else None,
            "output": str(output)[:500] if output else None,
            "elapsed_ms": round(elapsed_ms, 2),
            "status": status
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        return record
    
    def log_error(self, step_name: str, error: Exception, elapsed_ms: float):
        """记录错误"""
        return self.log(step_name, None, str(error), elapsed_ms, status="error")
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的执行"""
        last_error = None
        step_name = self.current_task or "unnamed"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                start = time.time()
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                self.log(step_name, {"args": str(args)[:200], "kwargs": str(kwargs)[:200]}, "ok", elapsed)
                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000 if 'start' in locals() else 0
                last_error = e
                self.log_error(step_name, e, elapsed)
                
                if attempt < self.max_retries:
                    wait = 2 ** attempt  # 指数退避
                    print(f"Retry {attempt}/{self.max_retries} after {wait}s: {e}")
                    time.sleep(wait)
                    
        raise last_error
    
    def get_recent_logs(self, hours: int = 24) -> list:
        """获取最近N小时的日志"""
        cutoff = datetime.now().timestamp() - hours * 3600
        logs = []
        
        for log_file in LOG_DIR.glob(f"{self.workflow_name}_*.jsonl"):
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        ts = datetime.fromisoformat(record["timestamp"]).timestamp()
                        if ts > cutoff:
                            logs.append(record)
                    except:
                        continue
        
        return sorted(logs, key=lambda x: x["timestamp"], reverse=True)
    
    def get_failed_steps(self) -> list:
        """获取失败的步骤"""
        failed = []
        for log_file in LOG_DIR.glob(f"{self.workflow_name}_*.jsonl"):
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if record["status"] == "error":
                            failed.append(record)
                    except:
                        continue
        return failed


def cleanup_old_logs(days: int = 7):
    """清理N天前的日志"""
    cutoff = datetime.now().timestamp() - days * 86400
    removed = 0
    
    for log_file in LOG_DIR.glob("*.jsonl"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            removed += 1
    
    return removed


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        n = cleanup_old_logs()
        print(f"Cleaned up {n} old log files")
    elif len(sys.argv) > 2:
        logger = TaskLogger(sys.argv[1])
        logs = logger.get_recent_logs(hours=int(sys.argv[2]))
        print(f"Recent {len(logs)} log entries:")
        for log in logs[:10]:
            print(f"  [{log['status']}] {log['step']} — {log['timestamp']}")
    else:
        print("Usage:")
        print("  python task_logger.py <workflow> <hours>  # 查看日志")
        print("  python task_logger.py cleanup             # 清理旧日志")
