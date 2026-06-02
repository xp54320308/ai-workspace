---
name: vector-memory
description: 用 ChromaDB 向量库替代硬编码 MEMORY 作为持久记忆系统
---

# Vector Memory System

Hermes 的持久记忆存储在用户已有的 ChromaDB 向量库中，使用 nomic-embed-text 做语义检索。

## 元数据
- 向量库路径: /mnt/f/RAG_Project/chroma_db
- Collection 名: hermes_memory
- Embedding 模型: nomic-embed-text (via Ollama localhost:11434)
- venv: /mnt/c/Users/qw/Documents/RAG_Project/venv

## 每次对话开头执行
```bash
cd /mnt/c/Users/qw/Documents/RAG_Project && source venv/bin/activate && python3 -c "
import chromadb, requests
from chromadb import Documents, EmbeddingFunction, Embeddings
class EF(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return [requests.post('http://localhost:11434/api/embeddings', json={'model':'nomic-embed-text','prompt':t}).json()['embedding'] for t in input]
client = chromadb.PersistentClient(path='/mnt/f/RAG_Project/chroma_db')
col = client.get_or_create_collection('hermes_memory', embedding_function=EF())
r = col.query(query_texts=['<当前话题>'], n_results=5)
for d, dist, m in zip(r['documents'][0], r['distances'][0], r['metadatas'][0]):
    print(f'[{m[\"category\"]}] dist={dist:.0f} | {d}')
"
```

## 写入新记忆
```bash
col.upsert(ids=['<id>'], documents=['<content>'], metadatas=[{'category': '<cat>'}])
```

## 注意
- 不要删除旧 collection，用 get_or_create_collection
- 如果 Ollama 没运行，回退到内置 MEMORY
- 距离小于400 算有意义的结果
