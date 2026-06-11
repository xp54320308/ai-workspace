"""
增量向量库操作

功能：
1. 增量添加文档
2. 增量更新文档
3. 增量删除文档
4. 批量操作优化
"""

import os
from typing import List, Dict, Optional, Set
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

from incremental_manager import IncrementalManager
from metadata_enricher import MetadataEnricher
from ingest_docs_v2 import load_and_split


class IncrementalVectorStore:
    """增量向量库操作"""
    
    def __init__(self, persist_dir: str, embedding_model: str = "nomic-embed-text",
                 state_file: str = "incremental_state.json"):
        """
        Args:
            persist_dir: 向量库持久化目录
            embedding_model: 嵌入模型名称
            state_file: 增量状态文件路径
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.state_file = state_file
        
        # 初始化组件
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.manager = IncrementalManager(state_file)
        self.enricher = MetadataEnricher()
        
        # 初始化向量库
        self.vectorstore = None
        self._init_vectorstore()
    
    def _init_vectorstore(self):
        """初始化向量库"""
        if os.path.exists(self.persist_dir):
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
            print(f"✅ 向量库加载成功: {self.persist_dir}")
        else:
            # 创建新的向量库
            os.makedirs(self.persist_dir, exist_ok=True)
            self.vectorstore = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
            print(f"✅ 向量库创建成功: {self.persist_dir}")
    
    def add_file(self, file_path: str, chunk_size: int = 800, 
                 chunk_overlap: int = 100) -> List[str]:
        """
        添加单个文件到向量库
        
        Args:
            file_path: 文件路径
            chunk_size: 块大小
            chunk_overlap: 块重叠
        
        Returns:
            添加的 chunk IDs
        """
        print(f"📄 添加文件: {os.path.basename(file_path)}")
        
        # 加载并切分文档
        chunks = load_and_split(file_path, chunk_size, chunk_overlap)
        if not chunks:
            print(f"⚠️ 文件为空或加载失败: {file_path}")
            return []
        
        # 添加到向量库
        chunk_ids = self.vectorstore.add_documents(chunks)
        
        # 更新状态
        self.manager.update_file_state(file_path, chunk_ids)
        
        print(f"✅ 添加成功: {len(chunk_ids)} 个文本块")
        return chunk_ids
    
    def update_file(self, file_path: str, chunk_size: int = 800,
                    chunk_overlap: int = 100) -> List[str]:
        """
        更新文件（先删除旧的，再添加新的）
        
        Args:
            file_path: 文件路径
            chunk_size: 块大小
            chunk_overlap: 块重叠
        
        Returns:
            新的 chunk IDs
        """
        print(f"🔄 更新文件: {os.path.basename(file_path)}")
        
        # 1. 删除旧的 chunks
        old_chunk_ids = self.manager.get_chunk_ids_for_file(file_path)
        if old_chunk_ids:
            try:
                self.vectorstore.delete(ids=old_chunk_ids)
                print(f"  🗑️  删除旧块: {len(old_chunk_ids)} 个")
            except Exception as e:
                print(f"  ⚠️ 删除旧块失败: {e}")
        
        # 2. 添加新的 chunks
        return self.add_file(file_path, chunk_size, chunk_overlap)
    
    def delete_file(self, file_path: str) -> int:
        """
        删除文件的所有 chunks
        
        Args:
            file_path: 文件路径
        
        Returns:
            删除的 chunk 数量
        """
        print(f"🗑️  删除文件: {os.path.basename(file_path)}")
        
        # 获取该文件的 chunk IDs
        chunk_ids = self.manager.get_chunk_ids_for_file(file_path)
        if not chunk_ids:
            print(f"  ⚠️ 未找到文件的 chunks: {file_path}")
            return 0
        
        # 从向量库删除
        try:
            self.vectorstore.delete(ids=chunk_ids)
            # 从状态中删除
            self.manager.remove_file_state(file_path)
            print(f"  ✅ 删除成功: {len(chunk_ids)} 个文本块")
            return len(chunk_ids)
        except Exception as e:
            print(f"  ❌ 删除失败: {e}")
            return 0
    
    def incremental_update(self, data_dir: str, supported_extensions: Set[str],
                          chunk_size: int = 800, chunk_overlap: int = 100) -> Dict[str, int]:
        """
        增量更新整个目录
        
        Args:
            data_dir: 数据目录
            supported_extensions: 支持的文件扩展名
            chunk_size: 块大小
            chunk_overlap: 块重叠
        
        Returns:
            更新统计：{'added': N, 'updated': N, 'deleted': N, 'unchanged': N}
        """
        print("=" * 50)
        print("🔄 增量更新开始")
        print("=" * 50)
        
        # 检测变化
        changes = self.manager.scan_directory(data_dir, supported_extensions)
        
        stats = {'added': 0, 'updated': 0, 'deleted': 0, 'unchanged': 0}
        
        for file_path, change_type in changes.items():
            if change_type == 'new':
                self.add_file(file_path, chunk_size, chunk_overlap)
                stats['added'] += 1
            elif change_type == 'modified':
                self.update_file(file_path, chunk_size, chunk_overlap)
                stats['updated'] += 1
            elif change_type == 'deleted':
                self.delete_file(file_path)
                stats['deleted'] += 1
            else:  # unchanged
                stats['unchanged'] += 1
        
        print("\n" + "=" * 50)
        print("📊 增量更新统计:")
        print(f"  ✅ 新增: {stats['added']} 个文件")
        print(f"  🔄 更新: {stats['updated']} 个文件")
        print(f"  🗑️  删除: {stats['deleted']} 个文件")
        print(f"  ⏭️  未变: {stats['unchanged']} 个文件")
        print("=" * 50)
        
        return stats
    
    def get_collection_stats(self) -> Dict:
        """获取向量库统计信息"""
        collection = self.vectorstore._collection
        return {
            "total_chunks": collection.count(),
            "persist_dir": self.persist_dir,
            "embedding_model": self.embedding_model,
            "file_stats": self.manager.get_stats()
        }
    
    def search_with_filter(self, query: str, filter_dict: Dict = None, 
                          k: int = 5) -> List[Document]:
        """
        带过滤的搜索
        
        Args:
            query: 查询文本
            filter_dict: 过滤条件，如 {"doc_type": "contract", "project": "fujinba"}
            k: 返回结果数量
        
        Returns:
            Document 列表
        """
        search_kwargs = {"k": k}
        if filter_dict:
            search_kwargs["filter"] = filter_dict
        
        retriever = self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        return retriever.invoke(query)


# 便捷函数
def create_incremental_store(persist_dir: str, embedding_model: str = "nomic-embed-text") -> IncrementalVectorStore:
    """创建增量向量库实例"""
    return IncrementalVectorStore(persist_dir, embedding_model)


if __name__ == "__main__":
    # 测试
    store = IncrementalVectorStore(
        persist_dir="/tmp/test_chroma_db",
        embedding_model="nomic-embed-text",
        state_file="/tmp/test_state.json"
    )
    
    # 测试添加文件
    test_file = "/mnt/c/Users/qw/Documents/RAG_Project/data/docker_intro.txt"
    if os.path.exists(test_file):
        chunk_ids = store.add_file(test_file)
        print(f"添加了 {len(chunk_ids)} 个 chunks")
    
    # 测试统计
    stats = store.get_collection_stats()
    print(f"\n统计: {stats}")
