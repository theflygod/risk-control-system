"""决策模块 — 评分汇总 → 风险等级 + 处理建议 → 触发案件创建
对应需求: 1.2.4 (风险等级 low/medium/high, 处理建议 pass/manual_review/reject,
          high/manual_review/reject 自动创建案件), 1.2.7 决策模块
"""

from typing import List, Dict, Any, Tuple
from app.config import SCORE_LOW_MAX, SCORE_MEDIUM_MAX


def calculate_total_score(hit_rules: List[Dict[str, Any]]) -> int:
    """累加所有命中规则的分值，100 分封顶"""
    total = sum(r["score"] for r in hit_rules)
    return min(total, 100)


def determine_risk_level(total_score: int) -> Tuple[str, str]:
    """根据总分映射风险等级和处理建议

    映射规则:
        0-30:  低风险 → 放行 (low / pass)
        31-60: 中风险 → 人工审核 (medium / manual_review)
        61-100: 高风险 → 拒绝 (high / reject)
    """
    if total_score <= SCORE_LOW_MAX:
        return "low", "pass"
    elif total_score <= SCORE_MEDIUM_MAX:
        return "medium", "manual_review"
    else:
        return "high", "reject"


def should_create_case(risk_level: str, decision: str) -> bool:
    """判断是否自动创建案件
    条件: risk_level == 'high' 或 decision in ('manual_review', 'reject')
    """
    return risk_level == "high" or decision in ("manual_review", "reject")


def make_decision(hit_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """完整的决策流程: 评分 → 等级 → 建议 → 是否创建案件

    输入: 命中规则列表
    输出: {"risk_score": 45, "risk_level": "medium",
            "decision": "manual_review", "auto_case": True}
    """
    total_score = calculate_total_score(hit_rules)
    risk_level, decision = determine_risk_level(total_score)
    auto_case = should_create_case(risk_level, decision)

    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "decision": decision,
        "auto_case": auto_case,
    }
