---
name: longterm-memory
version: 1.0.0
description: Persistent memory using vector embeddings for semantic search. Store insights to memory/vector/, retrieve with natural language queries, and maintain context across sessions.
triggers:
  - "remember this"
  - "search memory"
  - "what do you know about"
  - "find in memory"
  - "semantic search"
  - "recall"
tags: [memory, vector, embeddings, search, RAG]
allowed-tools:
  - terminal
  - read_file
  - write_file
  - search_files
required_commands:
  - python3
required_environment_variables:
  - OPENAI_API_KEY (or alternative embedding provider)
---

# Long-term Memory (Vector)

Persistent memory with semantic search.

## Setup

```bash
# Install dependencies
pip install chromadb openai tiktoken

# Configure API key
export OPENAI_API_KEY=sk-...
```

## Memory Directory

```
~/.openclaw/workspace/memory/vector/
├── chroma/
│   └── (ChromaDB persistent storage)
├── cache/
│   └── (Temporary embeddings)
└── logs/
    └── (Query logs)
```

## Store Memory

```python
import chromadb
from chromadb.config import Settings
from openai import OpenAI

client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="~/.openclaw/workspace/memory/vector/chroma"
))

# Create or get collection
collection = client.get_or_create_collection("memories")

# Embed and store
def store_memory(text, metadata=None):
    embedding = OpenAI().embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    collection.add(
        documents=[text],
        embeddings=[embedding.data[0].embedding],
        metadatas=[metadata or {"source": "user"}],
        ids=[f"mem_{len(collection.get()['ids'])}"]
    )
    return True

store_memory(
    "User prefers concise responses without apologies",
    metadata={"category": "preference", "priority": "high"}
)
```

## Query Memory

```python
def query_memory(query, n_results=5):
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results

# Example
results = query_memory("What are the user's communication preferences?")
for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
    print(f"{doc}\n(meta: {meta})\n")
```

## Search Patterns

```python
# By category
results = collection.query(
    query_texts=["preferences"],
    where={"category": "preference"}
)

# By priority
results = collection.query(
    query_texts=["important rules"],
    where={"priority": "high"}
)

# Combined
results = collection.query(
    query_texts=["user habits"],
    where={"category": "habit", "priority": {"$in": ["high", "critical"]}}
)
```

## Memory Management

```python
# Count memories
count = collection.count()
print(f"Total memories: {count}")

# List all (with metadata)
all_memories = collection.get()
for doc, meta in zip(all_memories['documents'], all_memories['metadatas']):
    print(f"[{meta.get('category', 'unknown')}] {doc[:100]}...")

# Delete by ID
collection.delete(ids=["mem_0", "mem_1"])

# Delete by filter
collection.delete(where={"category": "temp"})
```

## Periodic Cleanup

```bash
# Remove old/low-priority memories
python3 << 'EOF'
import chromadb
from chromadb.config import Settings

client = chromadb.Client(Settings(
    persist_directory="~/.openclaw/workspace/memory/vector/chroma"
))
collection = client.get_or_create_collection("memories")

# Delete memories older than 90 days with low priority
old_memories = collection.get()
for mem_id, meta in zip(old_memories['ids'], old_memories['metadatas']):
    if meta.get('priority') == 'low':
        collection.delete(ids=[mem_id])
EOF
```

## Query Log

```bash
# Check recent queries
tail -20 ~/.openclaw/workspace/memory/vector/logs/queries.log

# Find failed queries
grep "ERROR" ~/.openclaw/workspace/memory/vector/logs/queries.log
```

## Embedding Models

| Model | Dimensions | Cost | Speed |
|-------|------------|------|-------|
| text-embedding-3-small | 1536 | Low | Fast |
| text-embedding-3-large | 3072 | Medium | Medium |
| text-embedding-ada-002 | 1536 | Low | Fast |

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `AuthenticationError` | Invalid API key | Check OPENAI_API_KEY |
| `RateLimitError` | Too many requests | Add retry with backoff |
| `ImportError` | Missing library | pip install chromadb openai |

## Verification

```python
# Test embedding
from openai import OpenAI
result = OpenAI().embeddings.create(
    model="text-embedding-3-small",
    input="test"
)
print(f"Embedding length: {len(result.data[0].embedding)}")

# Test query
results = collection.query(query_texts=["test"], n_results=1)
print(f"Query successful: {results is not None}")
```

## Best Practices

1. **Chunk memories** - Don't store huge blocks; 100-500 tokens per memory
2. **Add metadata** - Categories, timestamps, priority help filtering
3. **Regular cleanup** - Remove stale/low-value memories
4. **Query expansion** - Use multiple query variants for better recall
