"""亚希自我进化 — 每日闭环工作流。

这是 Self-Evolution Engine 的实际使用入口。
在心跳、对话结束、出错时调用。

Usage:
    python evolve.py on_turn_end "用户消息" "助手回复"
    python evolve.py on_error "错误信息" "上下文"
    python evolve.py on_correction "用户纠正"
    python evolve.py maintain
    python evolve.py status
"""

import os
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from self_evolution import SelfEvolutionEngine

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")


def get_engine():
    return SelfEvolutionEngine(WORKSPACE)


def cmd_on_turn_end(user_msg: str, assistant_msg: str):
    engine = get_engine()
    engine.on_turn_end(user_msg, assistant_msg)
    print("OK: turn_end processed")


def cmd_on_error(error: str, context: str = ""):
    engine = get_engine()
    engine.on_error(error, context)
    print("OK: error recorded")


def cmd_on_correction(correction: str):
    engine = get_engine()
    engine.on_correction(correction)
    print("OK: correction recorded")


def cmd_maintain():
    engine = get_engine()
    report = engine.run_maintenance()
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_status():
    engine = get_engine()
    verification = engine.verify_improvements()
    patterns = engine._patterns

    status = {
        "learnings_file": engine._learnings_file,
        "learnings_exist": os.path.exists(engine._learnings_file),
        "patterns_exist": bool(patterns),
        "verification": verification,
        "pattern_counts": {
            "error_patterns": len(patterns.get("error_patterns", [])),
            "correction_patterns": len(patterns.get("correction_patterns", [])),
            "topic_patterns": len(patterns.get("topic_patterns", [])),
        },
    }
    print(json.dumps(status, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python evolve.py <on_turn_end|on_error|on_correction|maintain|status> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "on_turn_end":
        if len(sys.argv) < 4:
            print("Usage: python evolve.py on_turn_end 'user_msg' 'assistant_msg'")
            sys.exit(1)
        cmd_on_turn_end(sys.argv[2], sys.argv[3])
    elif cmd == "on_error":
        if len(sys.argv) < 3:
            print("Usage: python evolve.py on_error 'error' ['context']")
            sys.exit(1)
        cmd_on_error(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif cmd == "on_correction":
        if len(sys.argv) < 3:
            print("Usage: python evolve.py on_correction 'correction'")
            sys.exit(1)
        cmd_on_correction(sys.argv[2])
    elif cmd == "maintain":
        cmd_maintain()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
