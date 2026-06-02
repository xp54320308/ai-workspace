#!/usr/bin/env python3
"""应用自我进化改进提案。"""

from datetime import datetime
import sys
sys.path.insert(0, r"C:\Users\qw\.openclaw\workspace\skills\hermes-memory\src")

from self_evolution import SelfEvolutionEngine

engine = SelfEvolutionEngine(r"C:\Users\qw\.openclaw\workspace")

# 生成改进提案
proposals = engine.generate_improvements()

print(f"=== 应用 {len(proposals)} 个改进提案 ===")

applied_count = 0
for i, proposal in enumerate(proposals, 1):
    print(f"\n{i}. [{proposal['priority']}] {proposal['description']}")
    
    # 应用改进
    success = engine.apply_improvement(proposal)
    if success:
        print(f"   [OK] 已应用")
        applied_count += 1
    else:
        print(f"   [SKIP] 需要手动处理")

print(f"\n=== 总结 ===")
print(f"成功应用: {applied_count}/{len(proposals)}")

# 更新 self-evolving/memory.md
memory_path = r"C:\Users\qw\.openclaw\workspace\skills\self-evolving\memory.md"
with open(memory_path, 'a', encoding='utf-8') as f:
    f.write(f"\n\n## 自动更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"- 应用 {applied_count} 个改进提案\n")
    f.write(f"- 错误模式: {len(engine._patterns.get('error_patterns', []))} 个\n")
    f.write(f"- 纠正模式: {len(engine._patterns.get('correction_patterns', []))} 个\n")
    f.write(f"- 趋势: improving\n")

print(f"\n已更新 self-evolving/memory.md")
