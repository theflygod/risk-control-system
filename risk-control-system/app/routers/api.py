"""API 路由 — 15 个 REST 接口
对应需求: 1.2.9 接口要求

接口清单:
  风险检查:
    POST /api/risk/check           — 发起风险检查
    GET  /api/risk/assessments/{id} — 查询评估详情

  规则管理:
    GET    /api/risk/rules         — 规则列表
    POST   /api/risk/rules         — 新增规则
    POST   /api/risk/rules/update  — 更新规则
    POST   /api/risk/rules/status  — 启停用规则
    POST   /api/risk/rules/delete  — 删除规则

  案件管理:
    GET  /api/risk/cases           — 案件列表
    GET  /api/risk/cases/{id}      — 案件详情
    POST /api/risk/cases/review    — 审核案件

  黑名单:
    GET  /api/risk/blacklists      — 黑名单列表
    POST /api/risk/blacklists      — 新增黑名单
    POST /api/risk/blacklists/delete — 删除黑名单

  用户画像:
    GET /api/risk/users/{id}/profile — 用户画像

  看板:
    GET /api/risk/dashboard        — 看板统计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas import schemas
from app.services.event_service import process_risk_check
from app.services.case_service import get_cases, get_case_detail, review_case
from app.services.profile_service import get_user_profile
from app.services.dashboard_service import get_dashboard_stats
from app.models.models import (
    RiskRule, RiskAssessment, FeatureSnapshot, RuleHit,
    RiskCase, Blacklist,
)

router = APIRouter(prefix="/api/risk", tags=["risk-control"])


# ═══════════════════════════════════════════
# 风险检查
# ═══════════════════════════════════════════

@router.post("/check", response_model=schemas.RiskCheckResponse)
def risk_check(request: schemas.RiskCheckRequest, db: Session = Depends(get_db)):
    """发起风险检查: 事件→特征→规则→决策→案件(如需)"""
    if request.event_type not in ["order_create", "order_pay", "after_sale_apply", "logistics_complaint"]:
        raise HTTPException(status_code=400, detail=f"无效的事件类型: {request.event_type}")
    return process_risk_check(request, db)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_db)):
    """查询某次评估的详情(评分/等级/建议/命中规则/特征快照)"""
    assessment = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="评估记录不存在")

    # 命中规则
    rule_hits = db.query(RuleHit).filter(RuleHit.assessment_id == assessment_id).all()
    # 特征快照
    snapshot = db.query(FeatureSnapshot).filter(FeatureSnapshot.assessment_id == assessment_id).first()

    return {
        "assessment_id": assessment.id,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level,
        "decision": assessment.decision,
        "feature_snapshot": snapshot.feature_json if snapshot else {},
        "rule_hits": [
            {"rule_id": rh.rule_id, "hit_score": rh.hit_score, "hit_message": rh.hit_message}
            for rh in rule_hits
        ],
    }


# ═══════════════════════════════════════════
# 规则管理
# ═══════════════════════════════════════════

@router.get("/rules")
def list_rules(
    db: Session = Depends(get_db),
    rule_status: Optional[str] = Query(None, description="规则状态过滤"),
):
    """规则列表"""
    query = db.query(RiskRule)
    if rule_status:
        query = query.filter(RiskRule.rule_status == rule_status)
    rules = query.order_by(RiskRule.priority.desc()).all()
    return [
        {
            "id": r.id,
            "rule_code": r.rule_code,
            "rule_name": r.rule_name,
            "rule_status": r.rule_status,
            "priority": r.priority,
            "score": r.score,
            "condition_json": r.condition_json,
            "description": r.description,
            "hit_count": r.hit_count or 0,
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        }
        for r in rules
    ]


@router.post("/rules")
def create_rule(rule: schemas.RuleCreate, db: Session = Depends(get_db)):
    """新增规则"""
    existing = db.query(RiskRule).filter(RiskRule.rule_code == rule.rule_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"规则编码已存在: {rule.rule_code}")

    new_rule = RiskRule(
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        rule_status=rule.rule_status,
        priority=rule.priority,
        score=rule.score,
        condition_json=rule.condition_json,
        description=rule.description,
    )
    db.add(new_rule)
    db.commit()
    return {"status": "ok", "message": f"规则 {rule.rule_code} 创建成功", "rule_id": new_rule.id}


@router.post("/rules/update")
def update_rule(rule: schemas.RuleUpdate, rule_id: int = Query(..., description="规则ID"), db: Session = Depends(get_db)):
    """更新规则"""
    existing = db.query(RiskRule).filter(RiskRule.id == rule_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="规则不存在")
    # 排除值为 None 的字段，只更新提供的字段
    update_data = rule.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    db.commit()
    return {"status": "ok", "message": f"规则 {rule_id} 更新成功"}


@router.post("/rules/status")
def toggle_rule_status(
    toggle: schemas.RuleStatusToggle,
    rule_id: int = Query(..., description="规则ID"),
    db: Session = Depends(get_db),
):
    """启停用规则"""
    rule = db.query(RiskRule).filter(RiskRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    rule.rule_status = toggle.rule_status
    db.commit()
    return {"status": "ok", "message": f"规则 {rule_id} 状态已切换为 {toggle.rule_status}"}


@router.post("/rules/delete")
def delete_rules(body: schemas.RuleDelete, db: Session = Depends(get_db)):
    """删除规则（支持批量）"""
    deleted = db.query(RiskRule).filter(RiskRule.id.in_(body.rule_ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok", "message": f"已删除 {deleted} 条规则"}


# ═══════════════════════════════════════════
# 案件管理
# ═══════════════════════════════════════════

@router.get("/cases")
def list_cases(
    db: Session = Depends(get_db),
    case_status: Optional[str] = Query(None, description="案件状态过滤"),
    risk_level: Optional[str] = Query(None, description="风险等级过滤"),
):
    """案件列表"""
    return get_cases(db, case_status=case_status, risk_level=risk_level)


@router.get("/cases/{case_id}")
def case_detail(case_id: int, db: Session = Depends(get_db)):
    """案件详情"""
    detail = get_case_detail(case_id, db)
    if not detail:
        raise HTTPException(status_code=404, detail="案件不存在")
    return detail


@router.post("/cases/review")
def case_review(review: schemas.CaseReview, db: Session = Depends(get_db)):
    """审核案件"""
    result = review_case(
        case_id=review.case_id,
        reviewer_id="admin",  # 简化: 固定审核人
        review_result=review.review_result,
        review_remark=review.review_remark or "",
        db=db,
    )
    if not result:
        raise HTTPException(status_code=404, detail="案件不存在")
    return result


# ═══════════════════════════════════════════
# 黑名单管理
# ═══════════════════════════════════════════

@router.get("/blacklists")
def list_blacklists(
    db: Session = Depends(get_db),
    blacklist_type: Optional[str] = Query(None, description="黑名单类型过滤"),
):
    """黑名单列表"""
    query = db.query(Blacklist)
    if blacklist_type:
        query = query.filter(Blacklist.blacklist_type == blacklist_type)
    items = query.order_by(Blacklist.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "blacklist_type": b.blacklist_type,
            "blacklist_value": b.blacklist_value,
            "remark": b.remark,
            "status": b.status,
            "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
        }
        for b in items
    ]


@router.post("/blacklists")
def create_blacklist(body: schemas.BlacklistCreate, db: Session = Depends(get_db)):
    """新增黑名单"""
    item = Blacklist(
        blacklist_type=body.blacklist_type,
        blacklist_value=body.blacklist_value,
        remark=body.remark,
    )
    db.add(item)
    db.commit()
    return {"status": "ok", "message": "黑名单已添加", "id": item.id}


@router.post("/blacklists/delete")
def delete_blacklists(body: schemas.BlacklistDelete, db: Session = Depends(get_db)):
    """删除黑名单（批量）"""
    deleted = db.query(Blacklist).filter(Blacklist.id.in_(body.blacklist_ids)).delete(synchronize_session=False)
    db.commit()
    return {"status": "ok", "message": f"已删除 {deleted} 条黑名单"}


# ═══════════════════════════════════════════
# 用户画像
# ═══════════════════════════════════════════

@router.get("/users/{user_id}/profile")
def user_profile(user_id: str, db: Session = Depends(get_db)):
    """用户画像"""
    return get_user_profile(user_id, db)


# ═══════════════════════════════════════════
# 运营看板
# ═══════════════════════════════════════════

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    """看板统计"""
    return get_dashboard_stats(db)
