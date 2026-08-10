"""事件服务 — 风险检查主流程编排器
对应需求: 1.2.7 事件模块(接收请求/校验/写入), 1.2.4 (保存入参/快照/命中/结果)

主流程:
  POST /api/risk/check 请求
    → 写入 risk_events
    → compute_all_features() → 特征快照
    → match_rules() → 命中规则列表
    → make_decision() → 评分/等级/建议
    → 写入 risk_assessments + feature_snapshots + rule_hits
    → 如果 auto_case → 创建 risk_cases
    → 返回完整 RiskCheckResponse
"""

import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import (
    RiskEvent, RiskAssessment, FeatureSnapshot,
    RuleHit, RiskCase, ReviewLog,
)
from app.schemas.schemas import RiskCheckRequest, RiskCheckResponse, RuleHitItem
from app.services.feature_service import compute_all_features
from app.services.rule_engine import match_rules
from app.services.decision_service import make_decision


def process_risk_check(request: RiskCheckRequest, db: Session) -> RiskCheckResponse:
    """执行一次完整的风险检查

    Args:
        request: 包含 event_type, source_id, user_id, order_id
        db: 数据库会话

    Returns:
        RiskCheckResponse: 评估ID、评分、等级、建议、命中规则、特征快照、案件ID
    """

    # ── 第1步: 写入风险事件 ──
    event = RiskEvent(
        event_type=request.event_type,
        source_id=request.source_id,
        user_id=request.user_id,
        order_id=request.order_id,
        event_payload_json={"source": "api"},
    )
    db.add(event)
    db.flush()  # 获取 event.id，但暂不提交

    # ── 第2步: 计算特征快照 ──
    features = compute_all_features(request.user_id, request.order_id, request.event_type, db)

    # ── 第3步: 规则匹配 ──
    hit_rules = match_rules(features, db)

    # ── 第4步: 决策 ──
    decision_result = make_decision(hit_rules)

    # ── 第5步: 写入评估结果 ──
    assessment = RiskAssessment(
        event_id=event.id,
        risk_score=decision_result["risk_score"],
        risk_level=decision_result["risk_level"],
        decision=decision_result["decision"],
        assessment_status="completed",
    )
    db.add(assessment)
    db.flush()  # 获取 assessment.id

    # ── 第6步: 写入特征快照 ──
    snapshot = FeatureSnapshot(
        assessment_id=assessment.id,
        feature_json=features,
    )
    db.add(snapshot)

    # ── 第7步: 写入规则命中记录 ──
    for hit in hit_rules:
        rule_hit = RuleHit(
            assessment_id=assessment.id,
            rule_id=hit["rule_id"],
            hit_score=hit["score"],
            hit_message=hit["hit_message"],
        )
        db.add(rule_hit)

    # ── 第8步: 如需创建案件，自动创建 ──
    case_id: Optional[int] = None
    if decision_result["auto_case"]:
        risk_case = RiskCase(
            assessment_id=assessment.id,
            user_id=request.user_id,
            order_id=request.order_id,
            case_status="pending",
        )
        db.add(risk_case)
        db.flush()
        case_id = risk_case.id

    db.commit()

    # ── 第9步: 构造响应 ──
    rule_hit_items = [
        RuleHitItem(
            rule_name=h["rule_name"],
            rule_code=h["rule_code"],
            hit_score=h["score"],
            hit_message=h["hit_message"],
        )
        for h in hit_rules
    ]

    return RiskCheckResponse(
        assessment_id=assessment.id,
        risk_score=decision_result["risk_score"],
        risk_level=decision_result["risk_level"],
        decision=decision_result["decision"],
        rule_hits=rule_hit_items,
        feature_snapshot=features,
        case_id=case_id,
    )
