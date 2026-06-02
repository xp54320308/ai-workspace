"""MemoryManager — 记忆管理编排器，借鉴 Hermes Agent 架构。

编排内置 Provider + 最多一个外部 Plugin Provider。
单一集成点，所有记忆操作通过此管理器分发。

Usage:
    manager = MemoryManager()
    manager.add_provider(BuiltinFileProvider(...))
    # 可选：加一个外部 Provider
    # manager.add_provider(VectorDBProvider(...))

    # 系统提示
    prompt = manager.build_system_prompt()

    # 每轮对话前
    context = manager.prefetch_all(user_message)

    # 每轮对话后
    manager.sync_all(user_msg, assistant_response)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


class MemoryManager:
    """编排内置 Provider + 最多一个外部 Provider。

    - 内置 Provider（name="builtin"）永远第一个注册，不可移除
    - 外部 Provider 只允许一个，防止工具 schema 膨胀
    - 一个 Provider 失败不影响其他 Provider
    """

    def __init__(self) -> None:
        self._providers: List[MemoryProvider] = []
        self._tool_to_provider: Dict[str, MemoryProvider] = {}
        self._has_external: bool = False

    # -- 注册 ----------------------------------------------------------------

    def add_provider(self, provider: MemoryProvider) -> None:
        """注册记忆 Provider。

        内置 Provider（name="builtin"）始终接受。
        外部 Provider 只允许一个。
        """
        is_builtin = provider.name == "builtin"

        if not is_builtin:
            if self._has_external:
                existing = next(
                    (p.name for p in self._providers if p.name != "builtin"),
                    "unknown",
                )
                logger.warning(
                    "拒绝记忆 Provider '%s' — 外部 Provider '%s' 已注册。"
                    "同时只允许一个外部 Provider。",
                    provider.name, existing,
                )
                return
            self._has_external = True

        self._providers.append(provider)

        # 索引工具名 → Provider
        for schema in provider.get_tool_schemas():
            tool_name = schema.get("name", "")
            if tool_name and tool_name not in self._tool_to_provider:
                self._tool_to_provider[tool_name] = provider

        logger.info(
            "记忆 Provider '%s' 已注册（%d 个工具）",
            provider.name, len(provider.get_tool_schemas()),
        )

    @property
    def providers(self) -> List[MemoryProvider]:
        return list(self._providers)

    def get_provider(self, name: str) -> Optional[MemoryProvider]:
        for p in self._providers:
            if p.name == name:
                return p
        return None

    # -- 系统提示 ------------------------------------------------------------

    def build_system_prompt(self) -> str:
        """收集所有 Provider 的系统提示块。"""
        blocks = []
        for provider in self._providers:
            try:
                block = provider.system_prompt_block()
                if block and block.strip():
                    blocks.append(block)
            except Exception as e:
                logger.warning("Provider '%s' system_prompt_block 失败: %s", provider.name, e)
        return "\n\n".join(blocks)

    # -- 预取 ----------------------------------------------------------------

    def prefetch_all(self, query: str, *, session_id: str = "") -> str:
        """从所有 Provider 收集预取上下文。合并返回，失败不阻塞。"""
        parts = []
        for provider in self._providers:
            try:
                result = provider.prefetch(query, session_id=session_id)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                logger.debug("Provider '%s' prefetch 失败（非致命）: %s", provider.name, e)
        return "\n\n".join(parts)

    def queue_prefetch_all(self, query: str, *, session_id: str = "") -> None:
        """为下一轮排队后台预取。"""
        for provider in self._providers:
            try:
                provider.queue_prefetch(query, session_id=session_id)
            except Exception as e:
                logger.debug("Provider '%s' queue_prefetch 失败: %s", provider.name, e)

    # -- 同步 ----------------------------------------------------------------

    def sync_all(
        self, user_content: str, assistant_content: str, *, session_id: str = ""
    ) -> None:
        """同步一轮对话到所有 Provider。"""
        for provider in self._providers:
            try:
                provider.sync_turn(user_content, assistant_content, session_id=session_id)
            except Exception as e:
                logger.warning("Provider '%s' sync_turn 失败: %s", provider.name, e)

    # -- 工具 ----------------------------------------------------------------

    def get_all_tool_schemas(self) -> List[Dict[str, Any]]:
        """收集所有 Provider 的工具 schema。"""
        schemas = []
        seen = set()
        for provider in self._providers:
            try:
                for schema in provider.get_tool_schemas():
                    name = schema.get("name", "")
                    if name and name not in seen:
                        schemas.append(schema)
                        seen.add(name)
            except Exception as e:
                logger.warning("Provider '%s' get_tool_schemas 失败: %s", provider.name, e)
        return schemas

    def get_all_tool_names(self) -> set:
        return set(self._tool_to_provider.keys())

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tool_to_provider

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """路由工具调用到正确的 Provider。"""
        provider = self._tool_to_provider.get(tool_name)
        if provider is None:
            return '{"error": "No memory provider handles tool \'%s\'"}' % tool_name
        try:
            return provider.handle_tool_call(tool_name, args, **kwargs)
        except Exception as e:
            logger.error("Provider '%s' handle_tool_call(%s) 失败: %s", provider.name, tool_name, e)
            return '{"error": "Memory tool \'%s\' failed: %s"}' % (tool_name, e)

    # -- 生命周期钩子 --------------------------------------------------------

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        for provider in self._providers:
            try:
                provider.on_turn_start(turn_number, message, **kwargs)
            except Exception as e:
                logger.debug("Provider '%s' on_turn_start 失败: %s", provider.name, e)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        for provider in self._providers:
            try:
                provider.on_session_end(messages)
            except Exception as e:
                logger.debug("Provider '%s' on_session_end 失败: %s", provider.name, e)

    def on_pre_compress(self, messages: List[Dict[str, Any]]) -> str:
        """上下文压缩前，收集 Provider 的文本加入摘要。"""
        parts = []
        for provider in self._providers:
            try:
                result = provider.on_pre_compress(messages)
                if result and result.strip():
                    parts.append(result)
            except Exception as e:
                logger.debug("Provider '%s' on_pre_compress 失败: %s", provider.name, e)
        return "\n\n".join(parts)

    def on_memory_write(self, action: str, target: str, content: str) -> None:
        """内置记忆写入时通知外部 Provider。"""
        for provider in self._providers:
            if provider.name == "builtin":
                continue
            try:
                provider.on_memory_write(action, target, content)
            except Exception as e:
                logger.debug("Provider '%s' on_memory_write 失败: %s", provider.name, e)

    def on_delegation(
        self, task: str, result: str, *, child_session_id: str = "", **kwargs
    ) -> None:
        for provider in self._providers:
            try:
                provider.on_delegation(task, result, child_session_id=child_session_id, **kwargs)
            except Exception as e:
                logger.debug("Provider '%s' on_delegation 失败: %s", provider.name, e)

    def shutdown_all(self) -> None:
        for provider in reversed(self._providers):
            try:
                provider.shutdown()
            except Exception as e:
                logger.warning("Provider '%s' shutdown 失败: %s", provider.name, e)

    def initialize_all(self, session_id: str, **kwargs) -> None:
        for provider in self._providers:
            try:
                provider.initialize(session_id=session_id, **kwargs)
            except Exception as e:
                logger.warning("Provider '%s' initialize 失败: %s", provider.name, e)
