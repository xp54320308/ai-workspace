"""Example: 如何在 OpenClaw Agent 中使用 Hermes Memory System。"""

import os
import sys
import io

# 修复 Windows 终端编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加 skill 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import (
    MemoryManager,
    BuiltinFileProvider,
    build_memory_context_block,
)


def example_usage():
    """示例：完整的记忆系统使用流程。"""

    # === 1. 初始化 ===
    workspace_dir = os.path.expanduser("~/.openclaw/workspace")

    manager = MemoryManager()
    provider = BuiltinFileProvider(
        workspace_dir=workspace_dir,
        max_prefetch_chars=4000,
        max_search_results=5,
    )
    manager.add_provider(provider)
    manager.initialize_all(session_id="example-session")

    # === 2. 系统提示 ===
    system_prompt = manager.build_system_prompt()
    print("=== 系统提示 ===")
    print(system_prompt)
    print()

    # === 3. 每轮对话前：自动预取 ===
    user_message = "帮我写一个 Python 脚本"
    raw_context = manager.prefetch_all(user_message)

    # 用围栏包装
    fenced_context = build_memory_context_block(raw_context)
    print("=== 围栏记忆 ===")
    print(fenced_context[:500] if fenced_context else "(无相关记忆)")
    print()

    # === 4. 模型回复后：自动同步 ===
    assistant_response = "好的，我来帮你写一个 Python 脚本..."
    manager.sync_all(user_message, assistant_response)

    # === 5. 子 Agent 完成 ===
    manager.on_delegation(
        task="写一个 hello world 脚本",
        result="已创建 hello.py",
        child_session_id="sub-001",
    )

    # === 6. 上下文压缩前 ===
    messages = [
        {"role": "user", "content": "TODO: 优化数据库查询"},
        {"role": "assistant", "content": "✅ 已完成优化"},
    ]
    compress_text = manager.on_pre_compress(messages)
    print("=== 压缩前提取 ===")
    print(compress_text if compress_text else "(无待处理项)")
    print()

    # === 7. 清理 ===
    manager.shutdown_all()
    print("示例完成。")


if __name__ == "__main__":
    example_usage()
