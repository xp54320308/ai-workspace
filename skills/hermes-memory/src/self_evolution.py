"""Self-Evolution Engine — 统一自我进化闭环。

感知 → 学习 → 改进 → 验证，形成持续进化循环。

集成 5 个散装 skill 的能力：
- self-improving-agent → 感知层（错误/纠正捕获）
- self-evolving → 学习层（反思/模式提取）
- capability-evolver-pro → 改进层（提案生成）
- proactive-agent-lite → 主动层（反向提示）
- proactive-learner → 外界层（新知识吸收）

Usage:
    engine = SelfEvolutionEngine("~/.openclaw/workspace")
    engine.on_turn_end(user_msg, assistant_msg)       # 每轮结束
    engine.on_error(error, context)                    # 出错时
    engine.on_correction(user_correction)              # 用户纠正时
    engine.run_maintenance()                           # 心跳维护
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class SelfEvolutionEngine:
    """统一自我进化引擎。"""

    def __init__(self, workspace_dir: str):
        self._workspace = workspace_dir
        self._memory_dir = os.path.join(workspace_dir, "memory")
        self._skills_dir = os.path.join(workspace_dir, "skills")
        self._learnings_file = os.path.join(self._memory_dir, "learnings.jsonl")
        self._patterns_file = os.path.join(self._memory_dir, "patterns.json")
        self._evolution_log = os.path.join(self._memory_dir, "evolution-log.md")

        # 确保目录存在
        os.makedirs(self._memory_dir, exist_ok=True)

        # 内存缓存
        self._recent_learnings: List[Dict] = []
        self._patterns: Dict[str, Any] = self._load_patterns()

    # =========================================================================
    # 感知层 — 捕获信号
    # =========================================================================

    def on_turn_end(self, user_msg: str, assistant_msg: str) -> None:
        """每轮对话结束时调用。检测信号，决定是否需要学习。"""
        signals = self._detect_signals(user_msg, assistant_msg)

        if signals["should_learn"]:
            learning = {
                "timestamp": datetime.now().isoformat(),
                "type": signals["type"],
                "trigger": signals["trigger"],
                "user_msg": user_msg[:500],
                "assistant_msg": assistant_msg[:500],
                "tags": signals["tags"],
            }
            self._save_learning(learning)

        # 检查是否需要同步到日记
        if signals["should_sync"]:
            self._sync_to_daily(user_msg, assistant_msg, signals)

    def on_error(self, error: str, context: str = "") -> None:
        """出错时调用。记录错误模式。"""
        learning = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "trigger": "error_occurred",
            "error": error[:500],
            "context": context[:500],
            "tags": ["error"],
        }
        self._save_learning(learning)

        # 检查是否是重复错误
        if self._is_recurring_error(error):
            self._generate_fix_proposal(error)

    def on_correction(self, user_correction: str) -> None:
        """用户纠正时调用。这是最强的学习信号。"""
        learning = {
            "timestamp": datetime.now().isoformat(),
            "type": "correction",
            "trigger": "user_correction",
            "correction": user_correction[:500],
            "tags": ["correction", "high_priority"],
        }
        self._save_learning(learning)

    # =========================================================================
    # 学习层 — 提取模式
    # =========================================================================

    def extract_patterns(self) -> Dict[str, Any]:
        """从最近的 learnings 中提取模式。在心跳时调用。"""
        learnings = self._load_recent_learnings(days=7)
        if not learnings:
            return {}

        patterns = {
            "error_patterns": self._find_error_patterns(learnings),
            "correction_patterns": self._find_correction_patterns(learnings),
            "topic_patterns": self._find_topic_patterns(learnings),
            "extracted_at": datetime.now().isoformat(),
        }

        # 保存
        self._patterns.update(patterns)
        self._save_patterns()

        return patterns

    # =========================================================================
    # 改进层 — 生成提案
    # =========================================================================

    def generate_improvements(self) -> List[Dict[str, Any]]:
        """基于模式生成改进提案。"""
        proposals = []

        # 错误模式 → 修复提案
        for pattern in self._patterns.get("error_patterns", []):
            if pattern["count"] >= 3:  # 出现 3 次以上
                proposals.append({
                    "type": "fix_recurring_error",
                    "priority": "high",
                    "description": f"修复重复错误: {pattern['error_type']}",
                    "pattern": pattern,
                    "suggestion": self._suggest_fix(pattern),
                })

        # 纠正模式 → 行为调整提案
        for pattern in self._patterns.get("correction_patterns", []):
            if pattern["count"] >= 2:
                proposals.append({
                    "type": "behavior_adjustment",
                    "priority": "medium",
                    "description": f"调整行为: {pattern['topic']}",
                    "pattern": pattern,
                    "suggestion": self._suggest_behavior_change(pattern),
                })

        # 话题模式 → 知识补充提案
        for pattern in self._patterns.get("topic_patterns", []):
            if pattern["frequency"] >= 5:
                proposals.append({
                    "type": "knowledge_gap",
                    "priority": "low",
                    "description": f"知识补充: {pattern['topic']}",
                    "pattern": pattern,
                })

        return proposals

    def apply_improvement(self, proposal: Dict[str, Any]) -> bool:
        """应用改进提案。"""
        imp_type = proposal.get("type")

        if imp_type == "fix_recurring_error":
            return self._apply_error_fix(proposal)
        elif imp_type == "behavior_adjustment":
            return self._apply_behavior_change(proposal)
        elif imp_type == "knowledge_gap":
            return self._apply_knowledge_update(proposal)

        return False

    # =========================================================================
    # 验证层 — 追踪效果
    # =========================================================================

    def verify_improvements(self) -> Dict[str, Any]:
        """验证改进效果。"""
        learnings = self._load_recent_learnings(days=3)
        if not learnings:
            return {"status": "no_data"}

        # 计算错误率变化
        error_count = sum(1 for l in learnings if l.get("type") == "error")
        correction_count = sum(1 for l in learnings if l.get("type") == "correction")
        total = len(learnings)

        return {
            "period": "last_3_days",
            "total_learnings": total,
            "errors": error_count,
            "corrections": correction_count,
            "error_rate": error_count / total if total > 0 else 0,
            "correction_rate": correction_count / total if total > 0 else 0,
            "trend": self._calculate_trend(learnings),
        }

    # =========================================================================
    # 心跳维护
    # =========================================================================

    def run_maintenance(self) -> Dict[str, Any]:
        """心跳时运行的维护任务。"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "actions": [],
        }

        # 1. 提取模式
        patterns = self.extract_patterns()
        if patterns:
            report["actions"].append("patterns_extracted")

        # 2. 生成改进提案
        proposals = self.generate_improvements()
        if proposals:
            report["actions"].append(f"{len(proposals)}_proposals_generated")

            # 3. 自动应用低风险改进
            for p in proposals:
                if p["priority"] == "low":
                    if self.apply_improvement(p):
                        report["actions"].append(f"applied: {p['description']}")

        # 4. 验证效果
        verification = self.verify_improvements()
        report["verification"] = verification

        # 5. 清理旧 learnings（保留 30 天）
        cleaned = self._cleanup_old_learnings(days=30)
        if cleaned > 0:
            report["actions"].append(f"cleaned_{cleaned}_old_learnings")

        return report

    # =========================================================================
    # 内部方法
    # =========================================================================

    def _detect_signals(self, user_msg: str, assistant_msg: str) -> Dict[str, Any]:
        """检测对话中的学习信号。"""
        signals = {
            "should_learn": False,
            "should_sync": False,
            "type": "normal",
            "trigger": "",
            "tags": [],
        }

        user_lower = user_msg.lower()

        # 用户纠正信号（最强）
        correction_patterns = [
            r"不对|错了|不是这样|你搞错了|wrong|incorrect|actually",
            r"应该是|应该是|应该用|应该做",
            r"别再|不要|停止|don't|stop|never",
        ]
        for pattern in correction_patterns:
            if re.search(pattern, user_lower):
                signals["should_learn"] = True
                signals["type"] = "correction"
                signals["trigger"] = "user_correction_detected"
                signals["tags"].append("correction")
                break

        # 错误信号
        error_patterns = [
            r"error|exception|failed|traceback|报错|失败|出错",
            r"bug|issue|problem|问题",
        ]
        for pattern in error_patterns:
            if re.search(pattern, user_lower):
                signals["should_learn"] = True
                signals["type"] = "error"
                signals["trigger"] = "error_mentioned"
                signals["tags"].append("error")
                break

        # 学习信号
        learning_patterns = [
            r"学习|learn|研究|study|掌握|master",
            r"发现|discover|找到了|found",
            r"记住|remember|保存|save",
        ]
        for pattern in learning_patterns:
            if re.search(pattern, user_lower):
                signals["should_sync"] = True
                signals["tags"].append("learning")
                break

        # 决策信号
        decision_patterns = [
            r"决定|decide|选择|choose|确定|confirm",
            r"方案|plan|策略|strategy",
        ]
        for pattern in decision_patterns:
            if re.search(pattern, user_lower):
                signals["should_sync"] = True
                signals["tags"].append("decision")
                break

        return signals

    def _save_learning(self, learning: Dict) -> None:
        """保存一条 learning 到 JSONL 文件。"""
        self._recent_learnings.append(learning)
        try:
            with open(self._learnings_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(learning, ensure_ascii=False) + '\n')
        except Exception:
            pass

    def _load_recent_learnings(self, days: int = 7) -> List[Dict]:
        """加载最近 N 天的 learnings。"""
        if not os.path.exists(self._learnings_file):
            return []

        cutoff = datetime.now().timestamp() - (days * 86400)
        learnings = []

        try:
            with open(self._learnings_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        ts = item.get("timestamp", "")
                        if ts:
                            dt = datetime.fromisoformat(ts)
                            if dt.timestamp() > cutoff:
                                learnings.append(item)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception:
            pass

        return learnings

    def _load_patterns(self) -> Dict:
        """加载已保存的模式。"""
        if os.path.exists(self._patterns_file):
            try:
                with open(self._patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_patterns(self) -> None:
        """保存模式到文件。"""
        try:
            with open(self._patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self._patterns, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _find_error_patterns(self, learnings: List[Dict]) -> List[Dict]:
        """从 learnings 中找错误模式。"""
        errors = [l for l in learnings if l.get("type") == "error"]
        if not errors:
            return []

        # 按错误类型分组
        error_groups: Dict[str, List] = {}
        for e in errors:
            error_text = e.get("error", e.get("context", "unknown"))
            # 简单分类：取前 50 字符作为 key
            key = error_text[:50]
            error_groups.setdefault(key, []).append(e)

        return [
            {
                "error_type": key[:100],
                "count": len(group),
                "first_seen": group[0].get("timestamp"),
                "last_seen": group[-1].get("timestamp"),
            }
            for key, group in error_groups.items()
            if len(group) >= 2
        ]

    def _find_correction_patterns(self, learnings: List[Dict]) -> List[Dict]:
        """从 learnings 中找纠正模式。"""
        corrections = [l for l in learnings if l.get("type") == "correction"]
        if not corrections:
            return []

        # 按话题分组
        topic_groups: Dict[str, List] = {}
        for c in corrections:
            correction_text = c.get("correction", "")
            # 提取话题关键词
            topic = self._extract_topic(correction_text)
            topic_groups.setdefault(topic, []).append(c)

        return [
            {
                "topic": topic,
                "count": len(group),
                "examples": [g.get("correction", "")[:100] for g in group[:3]],
            }
            for topic, group in topic_groups.items()
            if len(group) >= 2
        ]

    def _find_topic_patterns(self, learnings: List[Dict]) -> List[Dict]:
        """从 learnings 中找话题频率模式。"""
        topic_freq: Dict[str, int] = {}
        for l in learnings:
            msg = l.get("user_msg", l.get("correction", l.get("error", "")))
            topic = self._extract_topic(msg)
            if topic:
                topic_freq[topic] = topic_freq.get(topic, 0) + 1

        return [
            {"topic": topic, "frequency": freq}
            for topic, freq in sorted(topic_freq.items(), key=lambda x: -x[1])
            if freq >= 3
        ]

    def _extract_topic(self, text: str) -> str:
        """从文本中提取话题关键词。"""
        # 简单实现：取第一个名词性短语
        keywords = [
            "OpenClaw", "Hermes", "Ollama", "Codex", "Python", "PowerShell",
            "记忆", "模型", "技能", "配置", "部署", "测试", "代码", "脚本",
            "飞书", "QQ", "微信", "Telegram", "Discord",
        ]
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                return kw
        # 取前 20 字符
        return text[:20] if text else "unknown"

    def _is_recurring_error(self, error: str) -> bool:
        """检查是否是重复错误。"""
        recent = self._load_recent_learnings(days=7)
        error_prefix = error[:50].lower()
        count = sum(
            1 for l in recent
            if l.get("type") == "error"
            and error_prefix in l.get("error", "").lower()
        )
        return count >= 3

    def _generate_fix_proposal(self, error: str) -> None:
        """为重复错误生成修复提案。"""
        proposal = {
            "timestamp": datetime.now().isoformat(),
            "type": "fix_proposal",
            "error": error[:200],
            "suggestion": self._suggest_fix({"error_type": error[:100], "count": 3}),
        }
        self._save_learning({
            "timestamp": datetime.now().isoformat(),
            "type": "proposal",
            "trigger": "recurring_error",
            "proposal": proposal,
            "tags": ["proposal", "auto_generated"],
        })

    def _suggest_fix(self, pattern: Dict) -> str:
        """根据错误模式建议修复方案。"""
        error_type = pattern.get("error_type", "").lower()

        if "encoding" in error_type or "codec" in error_type:
            return "添加 encoding='utf-8' 参数"
        elif "timeout" in error_type:
            return "增加 timeout 参数或添加重试逻辑"
        elif "permission" in error_type or "access" in error_type:
            return "检查文件权限或使用 elevated 执行"
        elif "not found" in error_type:
            return "检查路径是否正确，添加 exists 检查"
        elif "connection" in error_type or "network" in error_type:
            return "检查网络连接，添加重试逻辑"
        else:
            return "需要人工分析此错误模式"

    def _suggest_behavior_change(self, pattern: Dict) -> str:
        """根据纠正模式建议行为调整。"""
        topic = pattern.get("topic", "").lower()
        examples = pattern.get("examples", [])

        if any("简洁" in e or "太长" in e for e in examples):
            return "回复更简洁，减少解释"
        elif any("不要" in e or "别" in e for e in examples):
            return "避免重复用户明确禁止的行为"
        elif any("主动" in e for e in examples):
            return "更主动地提供建议和帮助"
        else:
            return f"关注 {topic} 相关的用户偏好"

    def _apply_error_fix(self, proposal: Dict) -> bool:
        """应用错误修复（记录到记忆）。"""
        suggestion = proposal.get("suggestion", "")
        if not suggestion:
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(self._memory_dir, f"{today}.md")
        timestamp = datetime.now().strftime("%H:%M")

        content = f"\n## 自动改进 ({timestamp})\n- 问题: {proposal.get('description', '')}\n- 修复: {suggestion}\n"
        try:
            with open(daily_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def _apply_behavior_change(self, proposal: Dict) -> bool:
        """应用行为调整（记录到记忆）。"""
        return self._apply_error_fix(proposal)

    def _apply_knowledge_update(self, proposal: Dict) -> bool:
        """应用知识补充（记录待学习话题）。"""
        topic = proposal.get("pattern", {}).get("topic", "")
        if not topic:
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(self._memory_dir, f"{today}.md")
        timestamp = datetime.now().strftime("%H:%M")

        content = f"\n## 待学习 ({timestamp})\n- 话题: {topic}\n- 频率: 用户频繁提及\n"
        try:
            with open(daily_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def _sync_to_daily(self, user_msg: str, assistant_msg: str, signals: Dict) -> None:
        """同步到每日日记。"""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = os.path.join(self._memory_dir, f"{today}.md")
        timestamp = datetime.now().strftime("%H:%M")

        tags = ", ".join(signals.get("tags", []))
        content = f"\n## 自动记录 ({timestamp}) [{tags}]\n- 用户: {user_msg[:100]}\n- 回复: {assistant_msg[:100]}\n"
        try:
            with open(daily_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass

    def _calculate_trend(self, learnings: List[Dict]) -> str:
        """计算趋势。"""
        if len(learnings) < 5:
            return "insufficient_data"

        # 前半段 vs 后半段的错误率
        mid = len(learnings) // 2
        first_half = learnings[:mid]
        second_half = learnings[mid:]

        first_errors = sum(1 for l in first_half if l.get("type") == "error")
        second_errors = sum(1 for l in second_half if l.get("type") == "error")

        first_rate = first_errors / len(first_half) if first_half else 0
        second_rate = second_errors / len(second_half) if second_half else 0

        if second_rate < first_rate * 0.8:
            return "improving"
        elif second_rate > first_rate * 1.2:
            return "degrading"
        else:
            return "stable"

    def _cleanup_old_learnings(self, days: int = 30) -> int:
        """清理旧 learnings。"""
        if not os.path.exists(self._learnings_file):
            return 0

        cutoff = datetime.now().timestamp() - (days * 86400)
        kept = []
        removed = 0

        try:
            with open(self._learnings_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        ts = item.get("timestamp", "")
                        if ts:
                            dt = datetime.fromisoformat(ts)
                            if dt.timestamp() > cutoff:
                                kept.append(line)
                            else:
                                removed += 1
                        else:
                            kept.append(line)
                    except (json.JSONDecodeError, ValueError):
                        kept.append(line)

            with open(self._learnings_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(kept) + '\n' if kept else '')

        except Exception:
            pass

        return removed
