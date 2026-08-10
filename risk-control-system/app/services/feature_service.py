"""特征计算服务 — 25 个风险特征
对应需求: 1.2.5 (25个特征, 用户/订单/地址三个维度), 1.2.7 特征模块

每个特征函数签名: calc_xxx(user_id, order_id, event_type, db) -> float/int/bool
最终由 compute_all_features() 汇总为特征快照字典
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import RiskEvent, RiskAssessment, Blacklist


def compute_all_features(user_id: str, order_id: str, event_type: str, db: Session) -> dict:
    """汇总 25 个特征，返回特征快照字典"""
    features = {}

    # === 用户维度 (10个) ===
    features.update(_calc_user_features(user_id, db))

    # === 订单维度 (10个) ===
    features.update(_calc_order_features(user_id, order_id, event_type, db))

    # === 地址维度 (5个) ===
    features.update(_calc_address_features(user_id, db))

    return features


def _calc_user_features(user_id: str, db: Session) -> dict:
    """用户维度特征 — 10 个"""
    f = {}

    # 1. 注册天数（用首次事件距今的天数模拟）
    first_event = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id
    ).order_by(RiskEvent.created_at).first()
    if first_event:
        f["registration_days"] = (datetime.now() - first_event.created_at).days
    else:
        f["registration_days"] = 0

    # 2. 历史订单数
    f["history_order_count"] = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type.in_(["order_create", "order_pay"])
    ).count()

    # 3. 退款率
    total_orders = f["history_order_count"]
    refund_count = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type == "after_sale_apply"
    ).count()
    f["refund_rate"] = round(refund_count / total_orders, 2) if total_orders > 0 else 0.0

    # 4. 投诉次数
    f["complaint_count"] = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.event_type == "logistics_complaint"
    ).count()

    # 5. 地址数量（从事件 payload 中提取的不同地址数 — 这里用 order_id 种类模拟）
    f["address_count"] = db.query(RiskEvent.order_id).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id.isnot(None)
    ).distinct().count()

    # 6. 设备更换频率（用 source_id 种类模拟）
    f["device_change_count"] = db.query(RiskEvent.source_id).filter(
        RiskEvent.user_id == user_id
    ).distinct().count()

    # 7. 历史高风险次数
    f["history_high_risk_count"] = db.query(RiskAssessment).join(
        RiskEvent, RiskAssessment.event_id == RiskEvent.id
    ).filter(
        RiskEvent.user_id == user_id,
        RiskAssessment.risk_level == "high"
    ).count()

    # 8. 是否命中黑名单
    blacklist = db.query(Blacklist).filter(
        Blacklist.blacklist_type == "user_id",
        Blacklist.blacklist_value == user_id,
        Blacklist.status == "active"
    ).first()
    f["blacklist_hit"] = blacklist is not None

    # 9. 账号绑定手机数（模拟值）
    f["bound_phone_count"] = 1

    # 10. 最近活跃间隔（天数）
    last_event = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id
    ).order_by(RiskEvent.created_at.desc()).first()
    if last_event:
        f["last_active_days_ago"] = (datetime.now() - last_event.created_at).days
    else:
        f["last_active_days_ago"] = 999

    return f


def _calc_order_features(user_id: str, order_id: str, event_type: str, db: Session) -> dict:
    """订单维度特征 — 10 个"""
    f = {}

    # 1. 订单金额（从 payload 中取，无则用模拟值）
    event = db.query(RiskEvent).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id == order_id
    ).order_by(RiskEvent.created_at.desc()).first()

    payload = event.event_payload_json if event else {}
    f["order_amount"] = float(payload.get("amount", 1000))

    # 2. 商品数量
    f["order_item_count"] = int(payload.get("item_count", 1))

    # 3. 收货地址与历史一致性（模拟：同一 user 不同订单数>5 则可能不一致）
    distinct_orders = db.query(RiskEvent.order_id).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id.isnot(None)
    ).distinct().count()
    f["address_matches_history"] = distinct_orders <= 5

    # 4. 下单时间段（小时）
    f["order_hour"] = datetime.now().hour

    # 5. 支付方式
    f["payment_method"] = payload.get("payment_method", "credit_card")

    # 6. 优惠金额占比
    discount = float(payload.get("discount", 0))
    f["discount_ratio"] = round(discount / f["order_amount"], 2) if f["order_amount"] > 0 else 0.0

    # 7. 订单备注长度
    note = payload.get("note", "")
    f["order_note_length"] = len(note)

    # 8. 是否大促期间（11月/6月/12月）
    month = datetime.now().month
    f["is_promotion_period"] = month in [6, 11, 12]

    # 9. 物流方式
    f["logistics_method"] = payload.get("logistics", "express")

    # 10. 是否跨境
    f["is_cross_border"] = payload.get("is_cross_border", False)

    return f


def _calc_address_features(user_id: str, db: Session) -> dict:
    """地址维度特征 — 5 个"""
    f = {}

    # 1. 地址匹配度（模拟值 0-1）
    f["address_match_score"] = 0.85

    # 2. 地址使用人数（同一 order_id 被不同用户使用的次数模拟）
    user_orders = db.query(RiskEvent.order_id).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id.isnot(None)
    ).distinct().all()
    order_ids = [o[0] for o in user_orders]
    if order_ids:
        other_users = db.query(RiskEvent.user_id).filter(
            RiskEvent.order_id.in_(order_ids),
            RiskEvent.user_id != user_id
        ).distinct().count()
        f["address_user_count"] = other_users + 1
    else:
        f["address_user_count"] = 1

    # 3. 地址变更次数（用不同 order_id 数量模拟）
    f["address_change_count"] = db.query(RiskEvent.order_id).filter(
        RiskEvent.user_id == user_id,
        RiskEvent.order_id.isnot(None)
    ).distinct().count()

    # 4. 地址历史风险次数
    f["address_history_risk_count"] = 0  # 简化

    # 5. GPS 与收货地址偏差（km，模拟值）
    f["gps_address_deviation"] = 5.0

    # 黑名单检查：检查地址关键词
    address_blacklist = db.query(Blacklist).filter(
        Blacklist.blacklist_type == "address_keyword",
        Blacklist.status == "active"
    ).count()
    if address_blacklist > 0:
        f["address_blacklist_hit"] = True
    else:
        f["address_blacklist_hit"] = False

    return f