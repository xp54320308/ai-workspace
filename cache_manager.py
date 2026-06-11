"""
缓存管理器

功能：
1. Embedding 缓存
2. 查询结果缓存
3. LRU 淘汰策略
4. 持久化存储
"""

import json
import hashlib
import sqlite3
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta


class EmbeddingCache:
    """Embedding 缓存"""
    
    def __init__(self, db_path="cache/embeddings.db", max_size=10000):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS embeddings (
            key TEXT PRIMARY KEY,
            text TEXT,
            embedding BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 1
        )''')
        conn.commit()
        conn.close()
    
    def _compute_key(self, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def get(self, text):
        key = self._compute_key(text)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT embedding FROM embeddings WHERE key = ?", (key,))
        result = cursor.fetchone()
        if result:
            cursor.execute("UPDATE embeddings SET last_accessed=CURRENT_TIMESTAMP, access_count=access_count+1 WHERE key=?", (key,))
            conn.commit()
            conn.close()
            return json.loads(result[0])
        conn.close()
        return None
    
    def set(self, text, embedding):
        key = self._compute_key(text)
        embedding_blob = json.dumps(embedding)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM embeddings WHERE key=?", (key,))
        if cursor.fetchone():
            cursor.execute("UPDATE embeddings SET embedding=?, last_accessed=CURRENT_TIMESTAMP WHERE key=?", (embedding_blob, key))
        else:
            cursor.execute("INSERT INTO embeddings (key, text, embedding) VALUES (?, ?, ?)", (key, text, embedding_blob))
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            count = cursor.fetchone()[0]
            if count > self.max_size:
                cursor.execute("DELETE FROM embeddings WHERE key IN (SELECT key FROM embeddings ORDER BY last_accessed ASC LIMIT ?)", (count - self.max_size,))
        conn.commit()
        conn.close()
    
    def get_stats(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM embeddings")
        count = cursor.fetchone()[0]
        conn.close()
        return {"size": count, "max_size": self.max_size}
    
    def clear(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM embeddings")
        conn.commit()
        conn.close()


class QueryResultCache:
    """查询结果缓存"""
    
    def __init__(self, db_path="cache/query_results.db", ttl_hours=24, max_size=1000):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.max_size = max_size
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS query_results (
            key TEXT PRIMARY KEY,
            query TEXT,
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 1
        )''')
        conn.commit()
        conn.close()
    
    def _compute_key(self, query, method="default", filter_dict=None):
        key_parts = [query, method]
        if filter_dict:
            key_parts.append(json.dumps(filter_dict, sort_keys=True))
        return hashlib.md5("|".join(key_parts).encode('utf-8')).hexdigest()
    
    def get(self, query, method="default", filter_dict=None):
        key = self._compute_key(query, method, filter_dict)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT results, created_at FROM query_results WHERE key=?", (key,))
        result = cursor.fetchone()
        if result:
            results_json, created_at = result
            created_time = datetime.fromisoformat(created_at)
            if datetime.now() - created_time > timedelta(hours=self.ttl_hours):
                cursor.execute("DELETE FROM query_results WHERE key=?", (key,))
                conn.commit()
                conn.close()
                return None
            cursor.execute("UPDATE query_results SET access_count=access_count+1 WHERE key=?", (key,))
            conn.commit()
            conn.close()
            return json.loads(results_json)
        conn.close()
        return None
    
    def set(self, query, results, method="default", filter_dict=None):
        key = self._compute_key(query, method, filter_dict)
        results_json = json.dumps(results, ensure_ascii=False)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT key FROM query_results WHERE key=?", (key,))
        if cursor.fetchone():
            cursor.execute("UPDATE query_results SET results=?, access_count=access_count+1 WHERE key=?", (results_json, key))
        else:
            cursor.execute("INSERT INTO query_results (key, query, results) VALUES (?, ?, ?)", (key, query, results_json))
            cursor.execute("SELECT COUNT(*) FROM query_results")
            count = cursor.fetchone()[0]
            if count > self.max_size:
                cursor.execute("DELETE FROM query_results WHERE key IN (SELECT key FROM query_results ORDER BY created_at ASC LIMIT ?)", (count - self.max_size,))
        conn.commit()
        conn.close()
    
    def get_stats(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM query_results")
        count = cursor.fetchone()[0]
        conn.close()
        return {"size": count, "max_size": self.max_size, "ttl_hours": self.ttl_hours}
    
    def clear(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_results")
        conn.commit()
        conn.close()


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir="cache", embedding_max_size=10000,
                 query_ttl_hours=24, query_max_size=1000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_cache = EmbeddingCache(str(self.cache_dir / "embeddings.db"), embedding_max_size)
        self.query_cache = QueryResultCache(str(self.cache_dir / "query_results.db"), query_ttl_hours, query_max_size)
    
    def get_embedding(self, text):
        return self.embedding_cache.get(text)
    
    def set_embedding(self, text, embedding):
        self.embedding_cache.set(text, embedding)
    
    def get_query_results(self, query, method="default", filter_dict=None):
        return self.query_cache.get(query, method, filter_dict)
    
    def set_query_results(self, query, results, method="default", filter_dict=None):
        self.query_cache.set(query, results, method, filter_dict)
    
    def get_stats(self):
        return {"embedding_cache": self.embedding_cache.get_stats(), "query_cache": self.query_cache.get_stats()}
    
    def clear_all(self):
        self.embedding_cache.clear()
        self.query_cache.clear()


if __name__ == "__main__":
    print("=== Cache Manager Test ===")
    cache = CacheManager(cache_dir="/tmp/test_cache")
    
    cache.set_embedding("test", [0.1, 0.2, 0.3])
    result = cache.get_embedding("test")
    print(f"Embedding cache: {result}")
    
    cache.set_query_results("query", [{"id": "1"}])
    result = cache.get_query_results("query")
    print(f"Query cache: {result}")
    
    print(f"Stats: {cache.get_stats()}")
    print("OK")
