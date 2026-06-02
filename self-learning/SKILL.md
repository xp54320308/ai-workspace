---
name: self-learning
version: 1.0.0
description: Self-improvement through reflection. Analyzes failures, generates insights, updates memory/self-learning/. Prevents repeating the same mistakes.
triggers:
  - "learn from"
  - "self-improve"
  - "reflect on"
  - "analyze failure"
  - "what went wrong"
  - "lessons learned"
tags: [learning, reflection, improvement, self]
allowed-tools:
  - read_file
  - write_file
  - search_files
---

# Self-Learning

Self-improvement through reflection and analysis.

## When to Use

- After a task fails or encounters errors
- When user corrects your approach
- When you discover a better way mid-task
- At session end, review what happened

## Learning Files

```
~/.openclaw/workspace/memory/self-learning/
├── reflections/      # Session reflections
│   └── YYYY-MM-DD.md
├── patterns/         # Identified patterns
│   └── anti-patterns.md
└── insights/         # Key learnings
    └── index.md
```

## Reflection Entry

```markdown
## [YYYY-MM-DD] Task: [Description]

### What Happened
Brief description of events.

### What Went Well
- Positive observation 1
- Positive observation 2

### What Could Be Better
- Issue 1
- Issue 2

### Root Cause (if failure)
Why did the issue occur?

### Action Items
- [ ] Specific improvement 1
- [ ] Specific improvement 2

### Tags
#reflection #task-type
```

## Pattern Detection

### Common Anti-Patterns

| Pattern | Symptom | Solution |
|---------|---------|----------|
| Assumption jumping | "I assumed X without verifying" | Always verify before acting |
| Narrow search | "I only checked one source" | Multi-source search |
| Over-engineering | "Simple task, complex solution" | Start simple, add complexity only if needed |
| Silent failure | "Something failed but I didn't notice" | Always check return values |
| Context loss | "I forgot about X from earlier" | Use memory systems |

### Pattern Entry

```markdown
## Anti-Pattern: [Name]

**Symptom:** What happens

**Cause:** Why it happens

**Prevention:** How to avoid

**Example:** Real occurrence

---
```

## Improvement Workflow

### After Errors

```python
def log_error_for_learning(error_info):
    entry = f"""## Error: {error_info['task']}

**Timestamp:** {datetime.now().isoformat()}
**Error:** {error_info['error']}
**Context:** {error_info['context']}

### Root Cause
{error_info.get('root_cause', 'Unknown')}

### Prevention
{error_info.get('prevention', 'TBD')}

---
"""
    append_to_file("~/.openclaw/workspace/memory/self-learning/reflections/errors.md", entry)
```

### After Success

```python
def log_success_insight(task, approach, outcome):
    entry = f"""## Success: {task}

**Approach:** {approach}
**Outcome:** {outcome}

### Key Insight
What made this work?

---
"""
    append_to_file("~/.openclaw/workspace/memory/self-learning/insights/successes.md", entry)
```

## Cross-Session Learning

### Query Past Learnings

```bash
# Find relevant past learnings
grep -r "authentication" ~/.openclaw/workspace/memory/self-learning/

# List recent reflections
ls -t ~/.openclaw/workspace/memory/self-learning/reflections/ | head -5
```

### Promote to Memory

When a learning becomes reliable guidance:

```python
def promote_to_guidance(learning_id, target_file):
    # Extract learning
    # Format as guidance
    # Append to target
    pass
```

Promotion targets:
- `~/.openclaw/workspace/SOUL.md` - Behavioral guidance
- `~/.openclaw/workspace/TOOLS.md` - Tool-specific patterns
- `~/.openclaw/workspace/AGENTS.md` - Workflow patterns

## Periodic Review

### Weekly Review

```python
def weekly_review():
    reflections = get_recent_reflections(days=7)
    errors = [r for r in reflections if "error" in r.lower()]
    successes = [r for r in reflections if "success" in r.lower()]
    
    summary = f"""## Weekly Self-Learning Review

### Errors (this week): {len(errors)}
{format_list(errors)}

### Successes (this week): {len(successes)}
{format_list(successes)}

### Pattern Changes
[Any new patterns identified]

### Recommended Focus
[What to improve next week]
"""
    return summary
```

## Self-Correction Triggers

Recognize and respond to:

| Trigger | Response |
|---------|----------|
| User says "No, that's wrong" | Log as correction, update approach |
| Command fails | Log error, try alternative |
| Assumed incorrectly | Log assumption, verify, continue |
| Found better way | Log insight, update approach |

## Verification

```bash
# Count learnings
find ~/.openclaw/workspace/memory/self-learning/ -name "*.md" | wc -l

# Recent errors
grep -l "Error:" ~/.openclaw/workspace/memory/self-learning/reflections/*.md | tail -3

# Check anti-patterns updated
tail -10 ~/.openclaw/workspace/memory/self-learning/patterns/anti-patterns.md
```

## Integration with Other Skills

- **continuous-learning** - Uses shared memory structure
- **longterm-memory** - Semantic search for past learnings
- **self-review** - Post-task review triggers self-learning
