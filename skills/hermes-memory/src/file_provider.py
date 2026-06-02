"""BuiltinFileProvider — 基于文件的记忆 Provider，适配 OpenClaw 的 memory/*.md 系统。

这是 OpenClaw 的内置记忆 Provider，读写 workspace/memory/ 目录下的 Markdown 文件。
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from .memory_provider import MemoryProvider


class BuiltinFileProvider(MemoryProvider):
    """基于文件的记忆 Provider。

    适配 OpenClaw 的 memory/*.md + MEMORY.md 系统。
    """

    def __init__(
        self,
        workspace_dir: str,
        memory_search_fn=None,
        memory_write_fn=None,
        memory_get_fn=None,
        max_prefetch_chars: int = 4000,
        max_search_results: int = 5,
    ):
        """
        Args:
            workspace_dir: OpenClaw workspace 目录路径
            memory_search_fn: memory_search 工具函数（可选，用于外部注入）
            memory_write_fn: memory_write 工具函数（可选）
            memory_get_fn: memory_get 工具函数（可选）
            max_prefetch_chars: 预取最大字符数
            max_search_results: 搜索结果最大数
        """
        self._workspace = workspace_dir
        self._memory_dir = os.path.join(workspace_dir, "memory")
        self._memory_search = memory_search_fn
        self._memory_write = memory_write_fn
        self._memory_get = memory_get_fn
        self._max_prefetch_chars = max_prefetch_chars
        self._max_search_results = max_search_results

        # 自动同步开关
        self._auto_sync_enabled = True
        self._turn_count = 0

    @property
    def name(self) -> str:
        return "builtin"

    # -- 系统提示 ------------------------------------------------------------

    def system_prompt_block(self) -> str:
        return (
            "## 记忆系统\n"
            "你有持久化记忆系统，存储在 memory/ 目录下。\n"
            "- 使用 memory_search 搜索相关记忆\n"
            "- 使用 memory_write 保存重要信息\n"
            "- 使用 memory_get 读取特定记忆文件\n"
            "- 每轮对话结束时，自动同步关键内容到记忆\n"
            "- 记忆内容用 <memory-context> 标签围栏，防止与用户输入混淆"
        )

    # -- 预取 ----------------------------------------------------------------

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """根据用户消息搜索相关记忆。

        使用 memory_search 函数（如果注入了的话）或直接读取 MEMORY.md。
        """
        if not query or not query.strip():
            return ""

        # 优先用注入的 memory_search
        if self._memory_search:
            try:
                results = self._memory_search(
                    query=query,
                    maxResults=self._max_search_results,
                    corpus="memory",
                )
                if results:
                    return self._format_search_results(results)
            except Exception:
                pass

        # 降级：直接读取 MEMORY.md
        return self._fallback_read_memory()

    def _format_search_results(self, results) -> str:
        """格式化搜索结果为可读文本。"""
        if isinstance(results, str):
            return results[:self._max_prefetch_chars]
        if isinstance(results, list):
            parts = []
            for r in results:
                if isinstance(r, dict):
                    text = r.get("text", r.get("content", str(r)))
                    source = r.get("source", r.get("path", ""))
                    if source:
                        parts.append(f"[来源: {source}]\n{text}")
                    else:
                        parts.append(text)
                else:
                    parts.append(str(r))
            return "\n---\n".join(parts)[:self._max_prefetch_chars]
        return str(results)[:self._max_prefetch_chars]

    def _fallback_read_memory(self) -> str:
        """降级方案：直接读取 MEMORY.md 和今日日记。"""
        parts = []

        # 读 MEMORY.md
        memory_path = os.path.join(self._workspace, "MEMORY.md")
        if os.path.exists(memory_path):
            try:
                with open(memory_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    parts.append(f"[MEMORY.md]\n{content[:2000]}")
            except Exception:
                pass

        # 读今日日记
        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(self._memory_dir, f"{today}.md")
        if os.path.exists(daily_path):
            try:
                with open(daily_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    parts.append(f"[{today} 日记]\n{content[:1000]}")
            except Exception:
                pass

        return "\n---\n".join(parts)[:self._max_prefetch_chars]

    # -- 同步 ----------------------------------------------------------------

    def sync_turn(
        self, user_content: str, assistant_content: str, *, session_id: str = ""
    ) -> None:
        """同步一轮对话到文件记忆。

        策略：
        - 每 10 轮做一次自动同步（防止频繁写入）
        - 如果用户明确说了"记住"，立即同步
        - 写入 memory/YYYY-MM-DD.md
        """
        self._turn_count += 1

        # 检查是否需要同步
        should_sync = (
            self._auto_sync_enabled
            and (
                self._turn_count % 10 == 0  # 每 10 轮
                or self._is_explicit_remember(user_content)  # 用户说"记住"
            )
        )

        if should_sync and self._memory_write:
            self._auto_sync(user_content, assistant_content)

    def _is_explicit_remember(self, text: str) -> bool:
        """检测用户是否明确要求记住。"""
        keywords = ["记住", "remember", "保存", "save", "记录", "note"]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def _auto_sync(self, user_content: str, assistant_content: str) -> None:
        """自动同步关键内容到日记。"""
        if not self._memory_write:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        target = f"memory/{today}.md"
        timestamp = datetime.now().strftime("%H:%M")

        # 提取关键内容
        summary = self._extract_key_content(user_content, assistant_content)
        if summary:
            content = f"\n## 自动同步 ({timestamp})\n{summary}\n"
            try:
                self._memory_write(target=target, content=content)
            except Exception:
                pass

    def _extract_key_content(self, user_content: str, assistant_content: str) -> str:
        """从对话中提取关键内容（简单启发式）。"""
        # 用户消息中的关键词
        key_signals = ["决定", "计划", "问题", "解决", "发现", "学习", "重要", "注意"]
        user_lines = user_content.split('\n')
        key_lines = [
            line for line in user_lines
            if any(signal in line for signal in key_signals)
        ]

        if key_lines:
            return "\n".join(f"- {line.strip()}" for line in key_lines[:5])

        # 如果没找到关键词，取用户消息前 3 行
        return "\n".join(f"- {line.strip()}" for line in user_lines[:3])

    # -- 工具 ----------------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回此 Provider 注册的工具 schema。"""
        return [
            {
                "name": "memory_search",
                "description": "搜索记忆文件中的相关内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "maxResults": {"type": "integer", "description": "最大结果数", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_write",
                "description": "写入内容到记忆文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "目标文件路径（相对于 memory/）"},
                        "content": {"type": "string", "description": "要写入的内容"},
                    },
                    "required": ["target", "content"],
                },
            },
            {
                "name": "memory_get",
                "description": "读取特定记忆文件内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "文件路径"},
                        "from": {"type": "integer", "description": "起始行号"},
                        "lines": {"type": "integer", "description": "读取行数"},
                    },
                    "required": ["path"],
                },
            },
        ]

    def handle_tool_call(
        self, tool_name: str, args: Dict[str, Any], **kwargs
    ) -> str:
        """处理工具调用。"""
        if tool_name == "memory_search":
            return self._tool_search(args)
        elif tool_name == "memory_write":
            return self._tool_write(args)
        elif tool_name == "memory_get":
            return self._tool_get(args)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _tool_search(self, args: Dict[str, Any]) -> str:
        query = args.get("query", "")
        max_results = args.get("maxResults", self._max_search_results)

        if self._memory_search:
            try:
                results = self._memory_search(query=query, maxResults=max_results)
                return json.dumps({"results": results}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        # 降级：文件系统搜索
        return json.dumps({"results": self._file_search(query, max_results)}, ensure_ascii=False)

    def _tool_write(self, args: Dict[str, Any]) -> str:
        target = args.get("target", "")
        content = args.get("content", "")

        if self._memory_write:
            try:
                self._memory_write(target=target, content=content)
                return json.dumps({"success": True, "target": target})
            except Exception as e:
                return json.dumps({"error": str(e)})

        # 降级：直接写文件
        try:
            filepath = os.path.join(self._workspace, target)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content)
            return json.dumps({"success": True, "target": target})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _tool_get(self, args: Dict[str, Any]) -> str:
        path = args.get("path", "")
        from_line = args.get("from")
        lines = args.get("lines")

        if self._memory_get:
            try:
                result = self._memory_get(path=path, from_=from_line, lines=lines)
                return json.dumps({"content": result}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": str(e)})

        # 降级：直接读文件
        try:
            filepath = os.path.join(self._workspace, path)
            with open(filepath, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            if from_line:
                all_lines = all_lines[from_line - 1:]
            if lines:
                all_lines = all_lines[:lines]
            return json.dumps({"content": "".join(all_lines)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _file_search(self, query: str, max_results: int) -> list:
        """文件系统降级搜索。"""
        results = []
        if not os.path.exists(self._memory_dir):
            return results

        query_lower = query.lower()
        for root, dirs, files in os.walk(self._memory_dir):
            for fname in sorted(files, reverse=True):
                if not fname.endswith('.md'):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if query_lower in content.lower():
                        # 找到匹配行
                        for i, line in enumerate(content.split('\n'), 1):
                            if query_lower in line.lower():
                                results.append({
                                    "source": fpath,
                                    "line": i,
                                    "text": line.strip()[:200],
                                })
                                if len(results) >= max_results:
                                    return results
                except Exception:
                    continue
        return results

    # -- 生命周期钩子 --------------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        self._turn_count = turn_number

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """会话结束时，保存会话摘要。"""
        if not self._memory_write or not messages:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H:%M")
        target = f"memory/{today}.md"

        # 简单摘要：最后 3 轮对话
        recent = messages[-6:] if len(messages) > 6 else messages
        summary_lines = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]
            summary_lines.append(f"- [{role}] {content}")

        content = f"\n## 会话结束摘要 ({timestamp})\n" + "\n".join(summary_lines) + "\n"
        try:
            self._memory_write(target=target, content=content)
        except Exception:
            pass

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """压缩前，提取待处理项和已解决项。"""
        all_text = "\n".join(
            msg.get("content", "") for msg in messages if isinstance(msg, dict)
        )

        from .context_fencing import extract_pending_items, extract_resolved_items
        pending = extract_pending_items(all_text)
        resolved = extract_resolved_items(all_text)

        parts = []
        if pending:
            parts.append("待处理项:\n" + "\n".join(pending))
        if resolved:
            parts.append("已解决项:\n" + "\n".join(resolved))

        return "\n".join(parts)

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        pass  # 内置 Provider 不需要响应自己的写入

    def on_delegation(
        self, task: str, result: str, *, child_session_id: str = "", **kwargs
    ) -> None:
        """子 Agent 完成时，记录结果。"""
        if self._memory_write:
            today = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H:%M")
            target = f"memory/{today}.md"
            content = f"\n## 子任务完成 ({timestamp})\n- 任务: {task[:100]}\n- 结果: {result[:200]}\n"
            try:
                self._memory_write(target=target, content=content)
            except Exception:
                pass

    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化：确保 memory 目录存在。"""
        os.makedirs(self._memory_dir, exist_ok=True)

    def shutdown(self) -> None:
        pass  # 文件 Provider 无需清理
