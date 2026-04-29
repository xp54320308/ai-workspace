"""
自动文档监听器

监控 data/ 目录，当有新文件添加、修改或删除时，自动重建向量库。

用法:
  python auto_ingest.py            # 前台运行 (Ctrl+C 停止)
  python auto_ingest.py --daemon   # 后台运行
"""

import os
import sys
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ====================================================================
#  配置
# ====================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PERSIST_DIR = "/mnt/f/RAG_Project/chroma_db"
EMBEDDING_MODEL = "nomic-embed-text"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# 防抖：文件变化后等待多少秒再重建（避免连续保存触发多次）
DEBOUNCE_SECONDS = 3

# 支持的文件格式
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".md", ".docx"}


# ====================================================================
#  向量库重建函数
# ====================================================================
def rebuild_vectorstore():
    """全量重建向量库"""
    print(f"\n{'='*50}")
    print(f"🔄 检测到文件变化，开始重建向量库...")
    print(f"{'='*50}")

    try:
        from ingest_docs import load_documents, split_documents
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma
        import shutil

        # 1. 加载文档
        docs = load_documents(DATA_DIR)
        if not docs:
            print("⚠️ 未找到文档，清空向量库")
            if os.path.exists(PERSIST_DIR):
                shutil.rmtree(PERSIST_DIR)
                os.makedirs(PERSIST_DIR, exist_ok=True)
            return

        # 2. 切片
        chunks = split_documents(docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        print(f"📄 {len(docs)} 文档 → {len(chunks)} 文本块")

        # 3. 清空旧向量库
        if os.path.exists(PERSIST_DIR):
            shutil.rmtree(PERSIST_DIR)
            os.makedirs(PERSIST_DIR, exist_ok=True)

        # 4. 向量化并存储
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=PERSIST_DIR,
        )

        print(f"✅ 向量库重建完成！{len(chunks)} 个文本块已索引")
        print(f"{'='*50}\n")

    except Exception as e:
        print(f"❌ 重建失败: {e}\n")


# ====================================================================
#  文件监听器
# ====================================================================
class DataDirHandler(FileSystemEventHandler):
    """监听 data/ 目录变化"""

    def __init__(self):
        super().__init__()
        self._timer = None
        self._lock = threading.Lock()

    def _schedule_rebuild(self, event_type: str, path: str):
        """防抖：延迟触发重建"""
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return

        print(f"📡 检测到变化: {event_type} → {os.path.basename(path)}")

        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, rebuild_vectorstore)
            self._timer.start()

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_rebuild("新建", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_rebuild("修改", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_rebuild("删除", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_rebuild("移动", event.dest_path)


# ====================================================================
#  主程序
# ====================================================================
def main():
    daemon_mode = "--daemon" in sys.argv

    print("=" * 50)
    print("👀 自动文档监听器")
    print("=" * 50)
    print(f"📂 监控目录: {os.path.abspath(DATA_DIR)}")
    print(f"💾 向量库:   {PERSIST_DIR}")
    print(f"⏱️  防抖延迟: {DEBOUNCE_SECONDS}s")
    print(f"📄 支持格式: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print("=" * 50)

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"📁 已创建数据目录: {DATA_DIR}")

    # 启动时先执行一次构建
    print("\n🚀 首次启动，执行初始构建...")
    rebuild_vectorstore()

    # 开始监听
    event_handler = DataDirHandler()
    observer = Observer()
    observer.schedule(event_handler, DATA_DIR, recursive=True)
    observer.start()

    print(f"👀 正在监听 {DATA_DIR} 目录...")
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
