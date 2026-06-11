import os
import sys

# 将 ingest_docs 的函数导入
from ingest_docs import load_documents, split_documents
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma


def setup_vectorstore(
    data_dir="data",
    persist_dir="/mnt/f/RAG_Project/chroma_db",
    embedding_model="nomic-embed-text",
    chunk_size=800,
    chunk_overlap=100,
    clear_old=False,
):
    """
    完整的向量库构建流程:
    加载文档(多格式) -> 切片 -> 向量化 -> 存入 ChromaDB
    """
    print("=" * 50)
    print("🚀 向量库构建管道")
    print("=" * 50)

    # 0. 清理旧数据 (可选)
    if clear_old and os.path.exists(persist_dir):
        import shutil
        shutil.rmtree(persist_dir)
        print(f"🗑️  已清空旧向量库")

    # 1. 检查并创建持久化目录
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir, exist_ok=True)
        print(f"📁 创建目录: {persist_dir}")

    print(f"📂 数据源: {os.path.abspath(data_dir)}")
    print(f"💾 存储路径: {persist_dir}")
    print(f"🤖 嵌入模型: {embedding_model}")
    print(f"📏 切片参数: chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    print()

    # 2. 加载文档 (支持 .txt, .pdf, .md, .docx)
    docs = load_documents(data_dir)
    if not docs:
        print("⚠️ 未找到任何文档，退出。")
        return
    print(f"\n✅ 共加载 {len(docs)} 个文档")

    # 3. 文本切片
    print("✂️  正在切片...")
    chunks = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    print(f"✅ 共生成 {len(chunks)} 个文本块")

    # 4. 初始化 Embedding 模型
    print(f"\n⏳ 正在生成向量 (可能需要较长时间)...")
    try:
        embeddings = OllamaEmbeddings(model=embedding_model)

        # 5. 创建 Chroma 向量库并持久化
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_dir,
        )

        print(f"\n{'=' * 50}")
        print(f"🎉 向量库构建成功！")
        print(f"💾 存储位置: {persist_dir}")
        print(f"📊 索引文档块数: {len(chunks)}")
        print(f"{'=' * 50}")

    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        print("💡 请确认 Ollama 正在运行且模型已下载")


if __name__ == "__main__":
    # === 配置参数 ===
    TARGET_PERSIST_PATH = "/mnt/f/RAG_Project/chroma_db"
    DATA_SOURCE_DIR = "data"
    EMBEDDING_MODEL = "nomic-embed-text"

    # 优化后的切片参数 (见第二步)
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100

    # 是否清空旧数据重建 (True = 全量重建)
    CLEAR_OLD = True

    setup_vectorstore(
        data_dir=DATA_SOURCE_DIR,
        persist_dir=TARGET_PERSIST_PATH,
        embedding_model=EMBEDDING_MODEL,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        clear_old=CLEAR_OLD,
    )
