"""MemoryProvider — 抽象基类，借鉴 Hermes Agent 的 Provider 模式。

所有记忆 Provider 必须实现这些方法。
MemoryManager 通过这个接口与 Provider 交互。
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class MemoryProvider(abc.ABC):
    """记忆 Provider 抽象基类。"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider 名称（如 'file', 'sqlite', 'vector'）。"""
        ...

    # -- 系统提示 ------------------------------------------------------------

    @abc.abstractmethod
    def system_prompt_block(self) -> str:
        """返回要注入系统提示的记忆指令块。

        例如告诉模型"你有记忆系统，可以使用 memory_search 工具"。
        """
        ...

    # -- 预取 / 回忆 ----------------------------------------------------------

    @abc.abstractmethod
    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """根据查询预取相关记忆，返回文本。

        在每轮对话开始前调用，为模型提供上下文。
        """
        ...

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """排队后台预取，为下一轮做准备。默认空实现。"""
        ...

    # -- 同步 ----------------------------------------------------------------

    @abc.abstractmethod
    def sync_turn(
        self, user_content: str, assistant_content: str, *, session_id: str = ""
    ) -> None:
        """同步一轮对话到记忆存储。

        每轮对话结束后调用。
        """
        ...

    # -- 工具 ----------------------------------------------------------------

    @abc.abstractmethod
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回此 Provider 注册的工具 schema 列表。

        格式：[{"name": "memory_search", "description": "...", "parameters": {...}}, ...]
        """
        ...

    @abc.abstractmethod
    def handle_tool_call(
        self, tool_name: str, args: Dict[str, Any], **kwargs
    ) -> str:
        """处理工具调用，返回 JSON 字符串结果。"""
        ...

    # -- 生命周期钩子 --------------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        """新轮次开始通知。"""
        ...

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """会话结束通知。"""
        ...

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """上下文压缩前通知，返回要加入压缩摘要的文本。"""
        return ""

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        """内置记忆写入通知（外部 Provider 接收）。"""
        ...

    def on_delegation(
        self, task: str, result: str, *, child_session_id: str = "", **kwargs
    ) -> None:
        """子 Agent 完成通知。"""
        ...

    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化 Provider。"""
        ...

    def shutdown(self) -> None:
        """关闭 Provider，释放资源。"""
        ...
