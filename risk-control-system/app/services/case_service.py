"""案件服务 — 案件列表/详情/审核/日志
对应需求: 1.2.7 案件模块(创建/审核/状态更新/日志), 1.2.4 案件状态流转
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import RiskCase, ReviewLog, RiskAssessment, FeatureSnapshot, RuleHit, RiskRule, RiskEvent


def get_cases(
    db: Session,
    case_status: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> List[dict]:
    """查询案件列表，支持状态和等级筛选"""
    query = db.query(RiskCase).join(
        RiskAssessment, RiskCase.assessment_id == RiskAssessment.id
    )

    if case_status:
        query = query.filter(RiskCase.case_status == case_status)
    if risk_level:
        query = query.filter(RiskAssessment.risk_level == risk_level)
    # 限制返回数量，避免一次性返回过多数据,按创建时间倒序排列
    cases = query.order_by(RiskCase.created_at.desc()).limit(100).all()

    return [
        {
            "case_id": c.id,
            "case_status": c.case_status,
            "risk_level": c.assessment.risk_level if c.assessment else "",
            "risk_score": c.assessment.risk_score if c.assessment else 0,
            "user_id": c.user_id,
            "order_id": c.order_id,
            "reviewer_id": c.reviewer_id,
            "review_result": c.review_result,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
        }
        for c in cases
    ]


def get_case_detail(case_id: int, db: Session) -> Optional[dict]:
    """查询案件详情，包含评估结果、命中规则、特征快照、审核日志"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        return None

    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.id == case.assessment_id
    ).first()

    if not assessment:
        return None

    # 特征快照
    snapshot = db.query(FeatureSnapshot).filter(
        FeatureSnapshot.assessment_id == assessment.id
    ).first()

    # 命中规则（联表查规则名）
    rule_hits = db.query(RuleHit, RiskRule).join(
        RiskRule, RuleHit.rule_id == RiskRule.id
    ).filter(
        RuleHit.assessment_id == assessment.id
    ).all()

    # 审核日志
    review_logs = db.query(ReviewLog).filter(
        ReviewLog.case_id == case_id
    ).order_by(ReviewLog.created_at).all()

    return {
        "case_id": case.id,
        "case_status": case.case_status,
        "review_result": case.review_result,
        "reviewer_id": case.reviewer_id,
        "user_id": case.user_id,
        "order_id": case.order_id,
        "assessment": {
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level,
            "decision": assessment.decision,
            "created_at": assessment.created_at.strftime("%Y-%m-%d %H:%M:%S") if assessment.created_at else "",
        },
        "rule_hits": [
            {
                "rule_name": rh[1].rule_name,
                "rule_code": rh[1].rule_code,
                "hit_score": rh[0].hit_score,
                "hit_message": rh[0].hit_message,
            }
            for rh in rule_hits
        ],
        "feature_snapshot": snapshot.feature_json if snapshot else {},
        "review_logs": [
            {
                "operator_id": rl.operator_id,
                "action_type": rl.action_type,
                "action_remark": rl.action_remark,
                "created_at": rl.created_at.strftime("%Y-%m-%d %H:%M:%S") if rl.created_at else "",
            }
            for rl in review_logs
        ],
    }


def review_case(case_id: int, reviewer_id: str, review_result: str, review_remark: str, db: Session) -> Optional[dict]:
    """审核案件: 通过(approved)或拒绝(rejected)"""
    case = db.query(RiskCase).filter(RiskCase.id == case_id).first()
    if not case:
        return None

    # 更新案件状态
    case.case_status = "reviewing"
    case.reviewer_id = reviewer_id
    case.review_result = review_result

    # 记录审核日志
    log = ReviewLog(
        case_id=case_id,
        operator_id=reviewer_id,
        action_type="approve" if review_result == "approved" else "reject",
        action_remark=review_remark,
    )
    db.add(log)

    # 根据审核结果更新案件状态
    if review_result == "approved":
        case.case_status = "approved"
    elif review_result == "rejected":
        case.case_status = "rejected"

    db.commit()

    return {
        "case_id": case.id,
        "case_status": case.case_status,
        "review_result": case.review_result,
        "message": f"案件 {case_id} 审核完成: {review_result}",
    }
