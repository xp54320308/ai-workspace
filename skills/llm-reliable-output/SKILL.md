---
name: llm-reliable-output
description: |
  When generating structured output from smaller LLMs (e.g., qwen2.5:14b, gemma, mistral via Ollama), 
  JSON output is unreliable — models frequently produce malformed JSON with Chinese quotes, trailing commas, 
  duplicate keys, or truncated output. This skill provides a proven alternative: tag-based metadata extraction.
  
  Trigger: any task requiring structured data from a local Ollama model that keeps failing JSON parsing.
---

# Reliable Structured Output from Local LLMs

## Problem
Smaller local models (qwen2.5:14b, gemma3, mistral via Ollama) are notoriously bad at producing valid JSON:
- Chinese curly quotes (`""`) mixed with standard quotes
- Trailing commas before `}` or `]`
- Duplicate keys in same object
- Content fields returning as `list` when `str` expected
- Output truncation mid-JSON

Multiple rounds of prompt engineering ("output valid JSON", "don't use markdown code blocks") rarely fix this.

## Solution: Tag-Based Metadata Extraction

Instead of asking the model to output JSON, have it output **plain text with metadata tags** at the top:

### Prompt Format
```
先用元数据标记开头（每行一个），然后直接写正文。

[TITLE: 主标题]
[SUBTITLE: 副标题]
[FIELD1: value1]
[FIELD2: value2]

---

（正文内容，用Markdown格式）
```

### Python Extraction
```python
import re

def extract_tag(raw: str, tag: str) -> str:
    m = re.search(rf'\[{tag}:\s*(.+?)\]', raw)
    return m.group(1).strip() if m else ""

# Extract all fields
title = extract_tag(raw, "TITLE")
subtitle = extract_tag(raw, "SUBTITLE")
score = extract_tag(raw, "SCORE")

# Extract body (everything after last metadata tag)
last_meta = 0
for m in re.finditer(r'\[[A-Z_]+:[^\]]*\]', raw):
    last_meta = max(last_meta, m.end())
body = raw[last_meta:].strip()
body = re.sub(r'^[-—\s]+', '', body)  # strip leading separator
```

## Why This Works
1. **No JSON syntax to get wrong** — tags are simple `[KEY: value]` pairs
2. **Chinese characters in values don't break parsing** — no quote escaping issues
3. **Body can be any format** — Markdown, plain text, whatever the model naturally produces
4. **Graceful degradation** — if a tag is missing, you get empty string, not parse error
5. **Models naturally understand the format** — they follow `[TAG: value]` patterns much better than JSON braces

## When to Use
- ✅ Ollama local models (qwen2.5, gemma, mistral, phi)
- ✅ Content generation tasks (articles, summaries, reports)
- ✅ When JSON parsing failure rate > 20%

## When NOT to Use
- ❌ Cloud APIs (GPT-4, Claude) — they handle JSON fine
- ❌ When downstream consumers strictly need JSON schema
- ❌ When you need nested structures (use JSON for those, or flatten to multiple tags)
