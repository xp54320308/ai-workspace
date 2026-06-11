"""
自动文档监听器 v2 - 支持增量更新

功能：
1. 监控 data/ 目录文件变化
2. 增量更新向量库（只处理变化的文件）
3. 防抖机制避免频繁更新
"""

import os
import sys
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from vectorstore_incremental import IncrementalVectorStore


# ====================================================================
#  配置
# ====================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PERSIST_DIR = "/mnt/f/RAG_Project/chroma_db"
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incremental_state.json")

# 防抖：文件变化后等待多少秒再更新
DEBOUNCE_SECONDS = 3

# 支持的文件格式
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".md", ".docx", ".xlsx"}


# ====================================================================
#  增量更新管理器
# ====================================================================
class IncrementalIngestManager:
    """增量摄入管理器"""
    
    def __init__(self):
        self.store = IncrementalVectorStore(
            persist_dir=PERSIST_DIR,
            embedding_model=EMBEDDING_MODEL,
            state_file=STATE_FILE
        )
        self._lock = threading.Lock()
    
    def process_file_change(self, file_path: str, change_type: str):
        """
        处理文件变化
        
        Args:
            file_path: 文件路径
            change_type: 变化类型：'created', 'modified', 'deleted'
        """
        with self._lock:
            try:
                if change_type == 'deleted':
                    self.store.delete_file(file_path)
                elif change_type in ('created', 'modified'):
                    if change_type == 'modified':
                        self.store.update_file(file_path, CHUNK_SIZE, CHUNK_OVERLAP)
                    else:
                        self.store.add_file(file_path, CHUNK_SIZE, CHUNK_OVERLAP)
                
                # 打印统计
                stats = self.store.get_collection_stats()
                print(f"📊 当前向量库: {stats['total_chunks']} 个文本块")
                
            except Exception as e:
                print(f"❌ 处理失败 [{change_type}] {file_path}: {e}")
    
    def full_scan(self):
        """全量扫描并更新"""
        with self._lock:
            print("\n🔍 全量扫描中...")
            stats = self.store.incremental_update(
                DATA_DIR, SUPPORTED_EXTENSIONS, CHUNK_SIZE, CHUNK_OVERLAP
            )
            return stats


# ====================================================================
#  文件监听器
# ====================================================================
class DataDirHandler(FileSystemEventHandler):
    """监听 data/ 目录变化"""

    def __init__(self, manager: IncrementalIngestManager):
        super().__init__()
        self.manager = manager
        self._timer = None
        self._pending_changes = {}
        self._lock = threading.Lock()

    def _schedule_update(self, event_type: str, path: str):
        """防抖：延迟触发更新"""
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return

        print(f"📡 检测到变化: {event_type} → {os.path.basename(path)}")

        with self._lock:
            # 记录变化
            self._pending_changes[path] = event_type
            
            # 重置定时器
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._process_pending_changes)
            self._timer.start()

    def _process_pending_changes(self):
        """处理所有待处理的变化"""
        with self._lock:
            changes = self._pending_changes.copy()
            self._pending_changes.clear()
        
        if not changes:
            return
        
        print(f"\n🔄 处理 {len(changes)} 个文件变化...")
        
        for file_path, change_type in changes.items():
            self.manager.process_file_change(file_path, change_type)
        
        print("✅ 增量更新完成\n")

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_update("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_update("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_update("deleted", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            # 移动 = 删除旧路径 + 创建新路径
            self._schedule_update("deleted", event.src_path)
            self._schedule_update("created", event.dest_path)


# ====================================================================
#  主程序
# ====================================================================
def main():
    daemon_mode = "--daemon" in sys.argv
    full_scan_mode = "--full-scan" in sys.argv

    print("=" * 50)
    print("👀 自动文档监听器 v2 (增量更新)")
    print("=" * 50)
    print(f"📂 监控目录: {os.path.abspath(DATA_DIR)}")
    print(f"💾 向量库:   {PERSIST_DIR}")
    print(f"⏱️  防抖延迟: {DEBOUNCE_SECONDS}s")
    print(f"📄 支持格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print(f"📊 状态文件: {STATE_FILE}")
    print("=" * 50)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"📁 已创建数据目录: {DATA_DIR}")

    # 初始化管理器
    manager = IncrementalIngestManager()

    # 首次启动执行全量扫描
    if full_scan_mode or not os.path.exists(STATE_FILE):
        print("\n🚀 首次启动，执行全量扫描...")
        manager.full_scan()
    else:
        print("\n🔄 增量模式，检测变化...")
        manager.full_scan()

    # 开始监听
    event_handler = DataDirHandler(manager)
    observer = Observer()
    observer.schedule(event_handler, DATA_DIR, recursive=True)
    observer.start()

    print(f"\n👀 正在监听 {DATA_DIR} 目录...")
    if daemon_mode:
        print("🔇 后台运行模式 (进程 PID:", os.getpid(), ")")
    else:
        print("⌨️  按 Ctrl+C 停止\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 停止监听...")
        observer.stop()

    observer.join()
    print("👋 已退出")


if __name__ == "__main__":
    main()
