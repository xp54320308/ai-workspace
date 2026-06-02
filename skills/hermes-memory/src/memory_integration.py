"""OpenClaw Memory Integration — 将 Hermes Memory 模式集成到 OpenClaw 会话流程。

此脚本可被心跳或 cron 调用，执行：
1. 记忆预取（搜索相关记忆）
2. 记忆同步（保存关键内容）
3. 记忆维护（清理过期内容）

Usage:
    python memory_integration.py prefetch "用户消息"
    python memory_integration.py sync "用户消息" "助手回复"
    python memory_integration.py maintain
"""

import os
import sys
import io
import json
import re
from datetime import datetime, timedelta

# 修复 Windows 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
MEMORY_DIR = os.path.join(WORKSPACE, "memory")
MEMORY_MD = os.path.join(WORKSPACE, "MEMORY.md")


def memory_search_file(query: str, max_results: int = 5) -> list:
    """文件系统记忆搜索。"""
    results = []
    if not os.path.exists(MEMORY_DIR):
        return results

    query_lower = query.lower()
    for root, dirs, files in os.walk(MEMORY_DIR):
        # 跳过隐藏目录和 .dreams
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'learned']
        for fname in sorted(files, reverse=True):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if query_lower in content.lower():
                    for i, line in enumerate(content.split('\n'), 1):
                        if query_lower in line.lower():
                            results.append({
                                "source": os.path.relpath(fpath, WORKSPACE),
                                "line": i,
                                "text": line.strip()[:200],
                            })
                            if len(results) >= max_results:
                                return results
            except Exception:
                continue
    return results


def prefetch(user_message: str) -> str:
    """预取相关记忆，返回围栏包裹的上下文。"""
    if not user_message or not user_message.strip():
        return ""

    # 搜索记忆
    results = memory_search_file(user_message)

    # 降级：读取 MEMORY.md + 今日日记
    if not results:
        parts = []
        if os.path.exists(MEMORY_MD):
            try:
                with open(MEMORY_MD, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    parts.append(f"[MEMORY.md 摘要]\n{content[:1500]}")
            except Exception:
                pass

        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(MEMORY_DIR, f"{today}.md")
        if os.path.exists(daily_path):
            try:
                with open(daily_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    parts.append(f"[{today} 日记]\n{content[:1000]}")
            except Exception:
                pass

        if parts:
            raw = "\n---\n".join(parts)
        else:
            return ""
    else:
        # 格式化搜索结果
        raw = "\n".join(
            f"[{r['source']}:{r['line']}] {r['text']}"
            for r in results
        )

    # 围栏包裹
    return (
        "<memory-context>\n"
        "[System note: recalled memory, NOT user input]\n\n"
        f"{raw}\n"
        "</memory-context>"
    )


def sync(user_message: str, assistant_response: str) -> bool:
    """同步关键内容到日记。"""
    # 检查是否需要同步
    key_signals = ["决定", "计划", "问题", "解决", "发现", "学习", "重要", "注意",
                   "remember", "记住", "保存", "save"]
    needs_sync = any(signal in user_message.lower() for signal in key_signals)

    if not needs_sync:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M")
    daily_path = os.path.join(MEMORY_DIR, f"{today}.md")

    # 提取关键内容
    user_lines = user_message.split('\n')
    key_lines = [
        line for line in user_lines
        if any(signal in line for signal in key_signals)
    ]

    if not key_lines:
        key_lines = user_lines[:3]

    summary = "\n".join(f"- {line.strip()}" for line in key_lines[:5])

    # 写入
    os.makedirs(MEMORY_DIR, exist_ok=True)
    content = f"\n## 自动同步 ({timestamp})\n{summary}\n"

    try:
        with open(daily_path, 'a', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"同步失败: {e}", file=sys.stderr)
        return False


def maintain() -> dict:
    """记忆维护：检查并清理过期内容。"""
    report = {"checked": 0, "issues": []}

    if not os.path.exists(MEMORY_DIR):
        return report

    # 检查今日日记是否存在
    today = datetime.now().strftime("%Y-%m-%d")
    daily_path = os.path.join(MEMORY_DIR, f"{today}.md")
    if not os.path.exists(daily_path):
        report["issues"].append(f"今日日记 {today}.md 不存在")

    # 检查 MEMORY.md 是否过大
    if os.path.exists(MEMORY_MD):
        size = os.path.getsize(MEMORY_MD)
        if size > 50000:  # 50KB
            report["issues"].append(f"MEMORY.md 过大: {size/1024:.1f}KB")

    # 统计记忆文件
    md_files = [f for f in os.listdir(MEMORY_DIR) if f.endswith('.md')]
    report["checked"] = len(md_files)

    # 检查是否有超过 30 天的日记
    cutoff = datetime.now() - timedelta(days=30)
    for fname in md_files:
        if re.match(r'\d{4}-\d{2}-\d{2}\.md$', fname):
            file_date = datetime.strptime(fname.replace('.md', ''), '%Y-%m-%d')
            if file_date < cutoff:
                report["issues"].append(f"旧日记: {fname} (>30天)")

    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python memory_integration.py <prefetch|sync|maintain> [args...]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "prefetch":
        if len(sys.argv) < 3:
            print("Usage: python memory_integration.py prefetch 'user message'")
            sys.exit(1)
        result = prefetch(sys.argv[2])
        print(result if result else "(无相关记忆)")

    elif action == "sync":
        if len(sys.argv) < 4:
            print("Usage: python memory_integration.py sync 'user msg' 'assistant reply'")
            sys.exit(1)
        success = sync(sys.argv[2], sys.argv[3])
        print("同步成功" if success else "无需同步")

    elif action == "maintain":
        report = maintain()
        print(json.dumps(report, ensure_ascii=False, indent=2))

    else:
        print(f"未知操作: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()
