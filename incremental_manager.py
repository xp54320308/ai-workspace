"""
增量更新管理器

功能：
1. 文件变化检测（哈希 + 修改时间）
2. 增量操作（新增/修改/删除）
3. 文件状态索引维护
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple


class FileState:
    """文件状态"""
    def __init__(self, path: str, hash: str, size: int, mtime: float, 
                 chunk_ids: List[str] = None):
        self.path = path
        self.hash = hash
        self.size = size
        self.mtime = mtime
        self.chunk_ids = chunk_ids or []
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "hash": self.hash,
            "size": self.size,
            "mtime": self.mtime,
            "chunk_ids": self.chunk_ids,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileState':
        state = cls(
            path=data["path"],
            hash=data["hash"],
            size=data["size"],
            mtime=data["mtime"],
            chunk_ids=data.get("chunk_ids", [])
        )
        state.last_updated = data.get("last_updated", datetime.now().isoformat())
        return state


class IncrementalManager:
    """增量更新管理器"""
    
    def __init__(self, state_file: str = "incremental_state.json"):
        """
        Args:
            state_file: 状态文件路径，存储文件哈希和 chunk ID 映射
        """
        self.state_file = Path(state_file)
        self.file_states: Dict[str, FileState] = {}
        self._load_state()
    
    def _load_state(self):
        """加载状态文件"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for path, state_dict in data.get("files", {}).items():
                    self.file_states[path] = FileState.from_dict(state_dict)
                print(f"加载状态文件: {len(self.file_states)} 个文件记录")
            except Exception as e:
                print(f"状态文件加载失败: {e}")
                self.file_states = {}
    
    def _save_state(self):
        """保存状态文件"""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "file_count": len(self.file_states),
            "files": {path: state.to_dict() for path, state in self.file_states.items()}
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def compute_file_hash(self, file_path: str) -> str:
        """计算文件哈希（MD5）"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_file_info(self, file_path: str) -> Optional[Tuple[str, int, float]]:
        """获取文件信息：(hash, size, mtime)"""
        try:
            stat = os.stat(file_path)
            file_hash = self.compute_file_hash(file_path)
            return file_hash, stat.st_size, stat.st_mtime
        except Exception:
            return None
    
    def scan_directory(self, data_dir: str, supported_extensions: Set[str]) -> Dict[str, str]:
        """
        扫描目录，检测文件变化
        
        Returns:
            变化的文件字典：{file_path: change_type}
            change_type: 'new', 'modified', 'deleted', 'unchanged'
        """
        changes = {}
        current_files = set()
        
        # 扫描当前文件
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    file_path = os.path.join(root, file)
                    current_files.add(file_path)
                    
                    file_info = self.get_file_info(file_path)
                    if file_info is None:
                        continue
                    
                    file_hash, size, mtime = file_info
                    
                    # 检查是否是新文件或已修改
                    if file_path not in self.file_states:
                        changes[file_path] = 'new'
                    else:
                        old_state = self.file_states[file_path]
                        if old_state.hash != file_hash:
                            changes[file_path] = 'modified'
                        else:
                            changes[file_path] = 'unchanged'
        
        # 检查删除的文件
        for path in list(self.file_states.keys()):
            if path not in current_files:
                changes[path] = 'deleted'
        
        return changes
    
    def update_file_state(self, file_path: str, chunk_ids: List[str]):
        """更新文件状态（处理完成后调用）"""
        file_info = self.get_file_info(file_path)
        if file_info is None:
            return
        
        file_hash, size, mtime = file_info
        self.file_states[file_path] = FileState(
            path=file_path,
            hash=file_hash,
            size=size,
            mtime=mtime,
            chunk_ids=chunk_ids
        )
        self._save_state()
    
    def remove_file_state(self, file_path: str) -> List[str]:
        """删除文件状态，返回该文件的 chunk IDs"""
        if file_path in self.file_states:
            chunk_ids = self.file_states[file_path].chunk_ids
            del self.file_states[file_path]
            self._save_state()
            return chunk_ids
        return []
    
    def get_chunk_ids_for_file(self, file_path: str) -> List[str]:
        """获取文件对应的所有 chunk IDs"""
        if file_path in self.file_states:
            return self.file_states[file_path].chunk_ids
        return []
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_chunks = sum(len(state.chunk_ids) for state in self.file_states.values())
        return {
            "total_files": len(self.file_states),
            "total_chunks": total_chunks,
            "state_file": str(self.state_file)
        }


# 便捷函数
def detect_changes(data_dir: str, supported_extensions: Set[str], 
                   state_file: str = "incremental_state.json") -> Dict[str, str]:
    """检测文件变化"""
    manager = IncrementalManager(state_file)
    return manager.scan_directory(data_dir, supported_extensions)


if __name__ == "__main__":
    # 测试
    manager = IncrementalManager("/tmp/test_state.json")
    
    # 模拟扫描
    test_dir = "/mnt/c/Users/qw/Documents/RAG_Project/data"
    extensions = {".txt", ".pdf", ".md", ".docx", ".xlsx"}
    
    changes = manager.scan_directory(test_dir, extensions)
    
    print("=== 文件变化检测 ===")
    for path, change_type in changes.items():
        if change_type != 'unchanged':
            print(f"  [{change_type}] {os.path.basename(path)}")
    
    print(f"\n统计: {manager.get_stats()}")
