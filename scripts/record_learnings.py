#!/usr/bin/env python3
"""手动记录最近的学习到进化引擎。"""

import sys
sys.path.insert(0, r"C:\Users\qw\.openclaw\workspace\skills\hermes-memory\src")

from self_evolution import SelfEvolutionEngine

engine = SelfEvolutionEngine(r"C:\Users\qw\.openclaw\workspace")

# 记录 1: ComfyUI 视频生成失败
engine.on_error(
    error="ComfyUI 视频生成失败：模型路径错误、VAE 不匹配（ae.safetensors 是 20 channels，但 svd_xt 期望 8 channels）",
    context="run_manga_5s_pipeline_v55_480p_first_last_test.py"
)

# 记录 2: API Keys 明文存储
engine.on_correction(
    user_correction="API Keys 不能明文存储在配置文件中，要用环境变量"
)

# 记录 3: Gateway 重启未告知
engine.on_error(
    error="执行安全加固时重启 Gateway，导致用户短暂断连",
    context="openclaw.json 环境变量配置"
)

# 记录 4: 编码问题
engine.on_error(
    error="evolution-plan.md 出现 UTF-8 编码乱码，4/28 的记录损坏",
    context="记忆文件编码问题"
)

# 记录 5: 工作流依赖检查
engine.on_correction(
    user_correction="执行工作流前要先检查所有依赖（模型、路径、版本），避免中途失败"
)

# 记录 6: 简洁沟通
engine.on_correction(
    user_correction="回复要简洁，不要 filler，直接说重点"
)

print('OK - 已记录 6 条学习')

# 运行维护
result = engine.run_maintenance()
print(f"维护结果: {result}")
