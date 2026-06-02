#!/usr/bin/env python3
"""分析自我进化状态。"""

import sys
sys.path.insert(0, r"C:\Users\qw\.openclaw\workspace\skills\hermes-memory\src")

from self_evolution import SelfEvolutionEngine

engine = SelfEvolutionEngine(r"C:\Users\qw\.openclaw\workspace")

# 提取模式
patterns = engine.extract_patterns()
print("=== 提取的模式 ===")
print(f"错误模式: {len(patterns.get('error_patterns', []))} 个")
print(f"纠正模式: {len(patterns.get('correction_patterns', []))} 个")
print(f"话题模式: {len(patterns.get('topic_patterns', []))} 个")

# 生成改进提案
proposals = engine.generate_improvements()
print(f"\n=== 改进提案 ({len(proposals)} 个) ===")
for i, p in enumerate(proposals, 1):
    print(f"{i}. [{p['priority']}] {p['description']}")
    if 'suggestion' in p:
        suggestion = p['suggestion']
        if isinstance(suggestion, str):
            print(f"   建议: {suggestion[:100]}...")
        else:
            print(f"   建议: {str(suggestion)[:100]}...")

# 验证效果
verification = engine.verify_improvements()
print(f"\n=== 验证结果 ===")
print(f"总学习数: {verification['total_learnings']}")
print(f"错误率: {verification['error_rate']:.2%}")
print(f"纠正率: {verification['correction_rate']:.2%}")
print(f"趋势: {verification['trend']}")
