"""规则引擎 — JSON 条件解析器 + 规则匹配
对应需求: 1.2.5 风险规则(24条规则, 支持 > < == in and or), 1.2.7 规则模块

核心设计:
- evaluate_condition(): 递归解析 condition_json，支持任意嵌套的 and/or/比较节点
- match_rules(): 遍历所有 enabled 规则，返回命中列表
- 规则改数据库即生效，不需要改代码
"""

import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import RiskRule


def evaluate_condition(condition: dict, features: Dict[str, Any]) -> bool:
    """递归解析 JSON 条件树，判断特征快照是否满足条件

    支持三种节点:
    - 比较节点: {"field": "xxx", "op": ">", "value": 30}
    - AND 节点: {"and": [子条件1, 子条件2, ...]}
    - OR 节点:  {"or":  [子条件1, 子条件2, ...]}

    支持的运算符: > < >= <= == != in
    condition_eg:
    {
  "or": [
    {"field": "blacklist_hit", "op": "==", "value": true},
    {
      "and": [
        {"field": "refund_rate", "op": ">", "value": 0.3},
        {"field": "order_amount", "op": ">", "value": 5000}
      ]
    }
  ]
} 
    features_eg:
    {
    # 用户维度 (10个)
    "registration_days": 3,          # 注册仅3天
    "history_order_count": 1,        # 历史订单只有1个
    "refund_rate": 0.0,              # 退款率0%
    "complaint_count": 0,            # 投诉次数0
    "address_count": 1,              # 地址数量1个
    "device_change_count": 0,        # 设备更换次数0
    "history_high_risk_count": 0,    # 历史高风险次数0
    "blacklist_hit": False,          # 是否命中黑名单
    "bound_phone_count": 1,          # 绑定手机数
    "last_active_days_ago": 0,       # 最近活跃间隔（天）

    # 订单维度 (10个)
    "order_amount": 8500.0,          # 订单金额8500元
    "order_item_count": 12,          # 商品数量12件
    "address_matches_history": False,# 收货地址与历史不一致
    "order_hour": 2,                 # 凌晨2点下单
    "payment_method": "credit_card", # 支付方式
    "discount_ratio": 0.02,          # 优惠占比2%
    "order_note_length": 200,        # 备注长度
    "is_promotion_period": False,    # 是否大促期间
    "logistics_method": "express",   # 物流方式
    "is_cross_border": False,        # 是否跨境

    # 地址维度 (5个)
    "address_match_score": 0.3,      # 地址匹配度30%
    "address_user_count": 8,         # 该地址被8个用户使用
    "address_change_count": 0,       # 地址变更次数
    "address_history_risk_count": 2, # 地址历史风险次数2次
    "gps_address_deviation": 50.0,   # GPS与地址偏差50km
}
    """
    # 逻辑节点 — AND: 所有子条件为真才命中
    if "and" in condition:
        return all(evaluate_condition(child, features) for child in condition["and"])

    # 逻辑节点 — OR: 任一子条件为真即命中
    if "or" in condition:
        return any(evaluate_condition(child, features) for child in condition["or"])

    # 比较节点
    field = condition.get("field")
    op = condition.get("op")
    target = condition.get("value")
    actual = features.get(field)

    if actual is None:
        return False

    if op == ">":
        return actual > target
    if op == "<":
        return actual < target
    if op == ">=":
        return actual >= target
    if op == "<=":
        return actual <= target
    if op == "==":
        return actual == target
    if op == "!=":
        return actual != target
    if op == "in":
        return actual in target

    return False


def match_rules(features: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
    """遍历所有启用的规则，返回命中的规则列表

    Args:
        features: 特征快照字典，如 {"refund_rate": 0.5, "order_amount": 8000, ...}
        db: 数据库会话

    Returns:
        命中规则列表 [{"rule_id": 1, "rule_code": "...", "rule_name": "...", "score": 20, "hit_message": "..."}]
    """
    rules = (
        db.query(RiskRule)
        .filter(RiskRule.rule_status == "enabled")
        .order_by(RiskRule.priority.desc())
        .all()
    )
    # 
    hit_rules = []
    for rule in rules:
        try:
            condition = rule.condition_json
            # 有可能是字符串，需要先解析为字典
            if isinstance(condition, str):
                condition = json.loads(condition)
            if evaluate_condition(condition, features):
                hit_rules.append({
                    "rule_id": rule.id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "score": rule.score,
                    "hit_message": rule.description or f"命中规则: {rule.rule_name}",
                })
                # 更新命中次数
                rule.hit_count = (rule.hit_count or 0) + 1
        except Exception:
            # 单条规则解析失败不影响其他规则
            continue

    db.commit()
    return hit_rules
