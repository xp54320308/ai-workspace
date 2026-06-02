"""Hermes Memory — OpenClaw 记忆增强系统

借鉴 Hermes Agent 的 MemoryManager + Provider 架构，
为 OpenClaw 添加记忆围栏、自动预取、自动同步、生命周期钩子。

核心组件：
- MemoryProvider: 抽象基类
- MemoryManager: 编排器
- BuiltinFileProvider: 基于文件的内置 Provider
- context_fencing: 记忆围栏工具
"""

from .memory_provider import MemoryProvider
from .memory_manager import MemoryManager
from .file_provider import BuiltinFileProvider
from .context_fencing import (
    build_memory_context_block,
    build_compression_prefix,
    sanitize_context,
    extract_pending_items,
    extract_resolved_items,
)
from .self_evolution import SelfEvolutionEngine

__all__ = [
    "MemoryProvider",
    "MemoryManager",
    "BuiltinFileProvider",
    "SelfEvolutionEngine",
    "build_memory_context_block",
    "build_compression_prefix",
    "sanitize_context",
    "extract_pending_items",
    "extract_resolved_items",
]
