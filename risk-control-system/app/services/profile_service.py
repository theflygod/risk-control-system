"""用户画像服务 — 聚合用户的历史行为与风险画像
对应需求: 1.2.3 用户画像页, 1.2.7 画像模块
"""

from sqlalchemy.orm import Session
from app.models.models import RiskEvent, RiskAssessment, RiskCase


def get_user_profile(user_id: str, db: Session) -> dict:
    """查询指定用户的风险画像

    Returns:
        {
            "user_id": "U10001",
            "history_order_count": 15,
            "refund_count": 2,
            "complaint_count": 1,
            "address_count": 3,
            "recent_risk_events": [...],
            "related_cases": [...]
        }
    """
    # 统计指标
    history_order_count = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type.in_(["order_create", "order_pay"]),
    ).count()

    refund_count = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type == "after_sale_apply",
    ).count()

    complaint_count = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type == "logistics_complaint",
    ).count()

    address_count = db.query(RiskEvent.order_id).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id.isnot(None),
    ).distinct().count()

    # 最近风险事件 (top 20)
    recent_events = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
    ).order_by(RiskEvent.created_at.desc()).limit(20).all()

    # 关联案件
    related_cases = db.query(RiskCase).filter(
        RiskCase.user_id == user_id,
    ).order_by(RiskCase.created_at.desc()).limit(20).all()

    return {
        "user_id": user_id,
        "history_order_count": history_order_count,
        "refund_count": refund_count,
        "complaint_count": complaint_count,
        "address_count": address_count,
        "recent_risk_events": [
            {
                "event_type": e.event_type,
                "order_id": e.order_id,
                "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
            }
            for e in recent_events
        ],
        "related_cases": [
            {
                "case_id": c.id,
                "case_status": c.case_status,
                "review_result": c.review_result,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            }
            for c in related_cases
        ],
    }
