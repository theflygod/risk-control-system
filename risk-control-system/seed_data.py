"""种子数据脚本 — 初始化 24 条规则 + 示例数据
对应需求: 1.2.5 (24条规则), 1.2.11 (完整演示链路)
运行: python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models.models import RiskRule, Blacklist, RiskEvent, RiskAssessment, FeatureSnapshot, RuleHit, RiskCase


def seed_rules():
    """插入 24 条风险规则，分 6 大类"""
    rules = [
        # ═══════════════ 黑名单类 (4条) ═══════════════
        {
            "rule_code": "BLACKLIST_USER",
            "rule_name": "用户黑名单命中",
            "priority": 100, "score": 50,
            "condition_json": {"field": "blacklist_hit", "op": "==", "value": True},
            "description": "该用户命中黑名单，直接标记高风险",
        },
        {
            "rule_code": "BLACKLIST_ADDRESS",
            "rule_name": "地址关键词黑名单",
            "priority": 90, "score": 35,
            "condition_json": {"field": "address_blacklist_hit", "op": "==", "value": True},
            "description": "收货地址关键词命中黑名单",
        },
        {
            "rule_code": "HIGH_RISK_HISTORY",
            "rule_name": "历史高风险用户",
            "priority": 80, "score": 25,
            "condition_json": {"field": "history_high_risk_count", "op": ">=", "value": 2},
            "description": "该用户历史上曾出现2次及以上高风险事件",
        },
        {
            "rule_code": "DEVICE_BLACKLIST",
            "rule_name": "设备更换频繁+历史风险",
            "priority": 70, "score": 20,
            "condition_json": {
                "and": [
                    {"field": "device_change_count", "op": ">", "value": 5},
                    {"field": "history_high_risk_count", "op": ">=", "value": 1},
                ]
            },
            "description": "设备更换超5次且曾有高风险记录",
        },

        # ═══════════════ 异常行为类 (6条) ═══════════════
        {
            "rule_code": "HIGH_FREQ_ORDER",
            "rule_name": "短时间内高频下单",
            "priority": 75, "score": 20,
            "condition_json": {
                "and": [
                    {"field": "history_order_count", "op": ">", "value": 20},
                    {"field": "last_active_days_ago", "op": "<=", "value": 1},
                ]
            },
            "description": "历史订单超20且最近1天内活跃，可能存在刷单嫌疑",
        },
        {
            "rule_code": "HIGH_REFUND_RATE",
            "rule_name": "退款率异常偏高",
            "priority": 75, "score": 25,
            "condition_json": {"field": "refund_rate", "op": ">", "value": 0.3},
            "description": "退款率超过30%，存在恶意退款风险",
        },
        {
            "rule_code": "FREQ_ADDRESS_CHANGE",
            "rule_name": "收货地址频繁变更",
            "priority": 65, "score": 15,
            "condition_json": {"field": "address_change_count", "op": ">", "value": 5},
            "description": "收货地址变更超过5次，可能存在地址欺诈",
        },
        {
            "rule_code": "MIDNIGHT_LARGE_ORDER",
            "rule_name": "深夜大额订单",
            "priority": 70, "score": 20,
            "condition_json": {
                "and": [
                    {"field": "order_hour", "op": ">=", "value": 0},
                    {"field": "order_hour", "op": "<=", "value": 5},
                    {"field": "order_amount", "op": ">", "value": 3000},
                ]
            },
            "description": "凌晨0-5点大额订单（>3000元），异常时段高风险",
        },
        {
            "rule_code": "MULTI_DEVICE",
            "rule_name": "多设备异常切换",
            "priority": 60, "score": 15,
            "condition_json": {"field": "device_change_count", "op": ">", "value": 5},
            "description": "同一用户使用5台以上不同设备，存在被盗号或欺诈风险",
        },
        {
            "rule_code": "HIGH_COMPLAINT",
            "rule_name": "投诉次数过多",
            "priority": 65, "score": 18,
            "condition_json": {"field": "complaint_count", "op": ">=", "value": 3},
            "description": "投诉次数>=3次，高投诉用户需关注",
        },

        # ═══════════════ 金额类 (4条) ═══════════════
        {
            "rule_code": "ABNORMAL_AMOUNT",
            "rule_name": "单笔金额异常",
            "priority": 70, "score": 20,
            "condition_json": {"field": "order_amount", "op": ">", "value": 10000},
            "description": "单笔订单金额超过10000元，需人工审核",
        },
        {
            "rule_code": "HIGH_DISCOUNT_RATIO",
            "rule_name": "优惠占比异常偏高",
            "priority": 50, "score": 10,
            "condition_json": {"field": "discount_ratio", "op": ">", "value": 0.5},
            "description": "优惠金额占比超50%，可能存在套取优惠风险",
        },
        {
            "rule_code": "CROSS_BORDER_AMOUNT",
            "rule_name": "跨境订单金额异常",
            "priority": 55, "score": 15,
            "condition_json": {
                "and": [
                    {"field": "is_cross_border", "op": "==", "value": True},
                    {"field": "order_amount", "op": ">", "value": 5000},
                ]
            },
            "description": "跨境订单金额超5000元，涉及关税与合规风险",
        },
        {
            "rule_code": "LARGE_ITEM_COUNT",
            "rule_name": "单笔订单商品数量异常",
            "priority": 50, "score": 12,
            "condition_json": {"field": "order_item_count", "op": ">", "value": 20},
            "description": "单笔订单商品数量超过20件，可能存在拆单或刷单",
        },

        # ═══════════════ 地址类 (4条) ═══════════════
        {
            "rule_code": "ADDRESS_NOT_MATCH",
            "rule_name": "收货地址与历史不一致",
            "priority": 55, "score": 10,
            "condition_json": {"field": "address_matches_history", "op": "==", "value": False},
            "description": "当前收货地址与用户历史地址不匹配",
        },
        {
            "rule_code": "ADDRESS_MULTI_USER",
            "rule_name": "地址被多人共用",
            "priority": 60, "score": 18,
            "condition_json": {"field": "address_user_count", "op": ">", "value": 5},
            "description": "同一地址被5人以上使用，可能存在团伙欺诈",
        },
        {
            "rule_code": "HIGH_RISK_REGION",
            "rule_name": "地址历史风险较高",
            "priority": 55, "score": 12,
            "condition_json": {"field": "address_history_risk_count", "op": ">=", "value": 2},
            "description": "该地址历史上关联过2次及以上风险事件",
        },
        {
            "rule_code": "GPS_DEVIATION_LARGE",
            "rule_name": "GPS与收货地址偏差大",
            "priority": 45, "score": 10,
            "condition_json": {"field": "gps_address_deviation", "op": ">", "value": 30},
            "description": "GPS定位与收货地址偏差超30km，地址真实性存疑",
        },

        # ═══════════════ 时序类 (3条) ═══════════════
        {
            "rule_code": "NEW_USER_LARGE_ORDER",
            "rule_name": "新注册用户大额订单",
            "priority": 80, "score": 30,
            "condition_json": {
                "and": [
                    {"field": "registration_days", "op": "<", "value": 7},
                    {"field": "order_amount", "op": ">", "value": 5000},
                ]
            },
            "description": "注册不到7天的新用户下单金额超5000元，高风险",
        },
        {
            "rule_code": "DORMANT_USER_SUDDEN",
            "rule_name": "长期沉睡用户突然活跃",
            "priority": 60, "score": 15,
            "condition_json": {
                "and": [
                    {"field": "last_active_days_ago", "op": ">", "value": 90},
                    {"field": "order_amount", "op": ">", "value": 2000},
                ]
            },
            "description": "90天未活跃用户突然下单超2000元，可能是账号被盗",
        },
        {
            "rule_code": "PROMOTION_ABUSE",
            "rule_name": "大促期间异常行为",
            "priority": 45, "score": 10,
            "condition_json": {
                "and": [
                    {"field": "is_promotion_period", "op": "==", "value": True},
                    {"field": "discount_ratio", "op": ">", "value": 0.6},
                ]
            },
            "description": "大促期间优惠占比超60%，需排查套利行为",
        },

        # ═══════════════ 组合类 (3条) ═══════════════
        {
            "rule_code": "ADDRESS_AMOUNT_COMBO",
            "rule_name": "地址异常+大额订单组合",
            "priority": 75, "score": 25,
            "condition_json": {
                "and": [
                    {"field": "address_matches_history", "op": "==", "value": False},
                    {"field": "order_amount", "op": ">", "value": 3000},
                ]
            },
            "description": "地址与历史不一致且订单金额超3000元，盗刷风险高",
        },
        {
            "rule_code": "REFUND_COMPLAINT_COMBO",
            "rule_name": "退款率高+投诉多",
            "priority": 70, "score": 22,
            "condition_json": {
                "and": [
                    {"field": "refund_rate", "op": ">", "value": 0.2},
                    {"field": "complaint_count", "op": ">=", "value": 2},
                ]
            },
            "description": "退款率超20%且投诉>=2次，恶意用户可能性大",
        },
        {
            "rule_code": "DEVICE_ADDRESS_COMBO",
            "rule_name": "多设备+多地址组合风险",
            "priority": 65, "score": 18,
            "condition_json": {
                "and": [
                    {"field": "device_change_count", "op": ">", "value": 3},
                    {"field": "address_change_count", "op": ">", "value": 3},
                ]
            },
            "description": "设备和地址都频繁更换，身份欺诈风险",
        },
    ]

    db = SessionLocal()
    try:
        for r in rules:
            existing = db.query(RiskRule).filter(RiskRule.rule_code == r["rule_code"]).first()
            if not existing:
                db.add(RiskRule(**r))
        db.commit()
        print(f"✅ 已插入 {len(rules)} 条规则")
    finally:
        db.close()


def seed_blacklists():
    """插入示例黑名单数据"""
    items = [
        # 用户黑名单
        {"blacklist_type": "user_id", "blacklist_value": "TB20240115003", "remark": "已确认欺诈-团伙A成员-关联3笔盗刷"},
        {"blacklist_type": "user_id", "blacklist_value": "TB20240308017", "remark": "恶意退款-累计退款23笔-金额超5万"},
        {"blacklist_type": "user_id", "blacklist_value": "TB20240622005", "remark": "账号被盗-多设备异地登录-已冻结"},
        # IP 黑名单
        {"blacklist_type": "ip_address", "blacklist_value": "103.45.67.89", "remark": "阿里云香港ECS-代理池出口IP"},
        {"blacklist_type": "ip_address", "blacklist_value": "45.33.32.156", "remark": "Linode美国节点-匿名代理"},
        {"blacklist_type": "ip_address", "blacklist_value": "198.58.118.42", "remark": "Tor出口节点-高风险"},
        # 设备黑名单
        {"blacklist_type": "device_id", "blacklist_value": "a1b2c3d4e5f6-ios-17.2", "remark": "越狱iPhone-关联3单欺诈"},
        {"blacklist_type": "device_id", "blacklist_value": "f0e1d2c3b4a5-android-14", "remark": "改机工具伪造设备指纹"},
        {"blacklist_type": "device_id", "blacklist_value": "11:22:33:44:55:66-emulator", "remark": "安卓模拟器-批量注册账号"},
        # 地址关键词黑名单
        {"blacklist_type": "address_keyword", "blacklist_value": "广东省深圳市宝安区西乡街道虚拟产业园", "remark": "虚假地址-无实际办公场所"},
        {"blacklist_type": "address_keyword", "blacklist_value": "浙江省义乌市江东街道货运市场3区", "remark": "刷单收货集散点-30日内关联50+异常订单"},
        {"blacklist_type": "address_keyword", "blacklist_value": "福建省泉州市晋江市陈埭镇自提柜", "remark": "自提柜地址-退换货率92%-疑似恶意"},
    ]

    db = SessionLocal()
    try:
        for item in items:
            existing = db.query(Blacklist).filter(
                Blacklist.blacklist_type == item["blacklist_type"],
                Blacklist.blacklist_value == item["blacklist_value"],
            ).first()
            if not existing:
                db.add(Blacklist(**item))
        db.commit()
        print(f"✅ 已插入 {len(items)} 条黑名单")
    finally:
        db.close()


def seed_demo_events():
    """插入演示用的风险事件数据，覆盖四类事件类型"""
    events = [
        # 正常用户下单 — 低风险
        {"event_type": "order_create", "source_id": "WEB-001", "user_id": "U10001", "order_id": "ORD-001",
         "event_payload_json": {"amount": 200, "item_count": 2, "payment_method": "alipay", "discount": 10, "note": ""}},
        # 新用户大额订单 — 高风险 (触发 NEW_USER_LARGE_ORDER)
        {"event_type": "order_create", "source_id": "APP-001", "user_id": "U20001", "order_id": "ORD-002",
         "event_payload_json": {"amount": 8000, "item_count": 1, "payment_method": "credit_card", "discount": 0, "note": "请尽快发货"}},
        # 黑名单用户下单 — 高风险 (触发 BLACKLIST_USER)
        {"event_type": "order_create", "source_id": "APP-003", "user_id": "TB20240115003", "order_id": "ORD-006",
         "event_payload_json": {"amount": 3500, "item_count": 3, "payment_method": "credit_card", "discount": 100, "note": ""}},
        # 高退款用户发起售后 — 中风险
        {"event_type": "after_sale_apply", "source_id": "APP-002", "user_id": "U30001", "order_id": "ORD-003",
         "event_payload_json": {"amount": 1500, "reason": "商品破损"}},
        # 物流投诉 — 中风险
        {"event_type": "logistics_complaint", "source_id": "WEB-002", "user_id": "U40001", "order_id": "ORD-004",
         "event_payload_json": {"reason": "包裹丢失"}},
        # 正常用户支付 — 低风险
        {"event_type": "order_pay", "source_id": "WEB-003", "user_id": "U10001", "order_id": "ORD-005",
         "event_payload_json": {"amount": 350, "item_count": 1, "payment_method": "wechat", "discount": 0, "note": ""}},
        # 深夜大额订单 — 中高风险 (触发 MIDNIGHT_LARGE_ORDER 如果深夜)
        {"event_type": "order_create", "source_id": "APP-004", "user_id": "U50001", "order_id": "ORD-007",
         "event_payload_json": {"amount": 12000, "item_count": 5, "payment_method": "credit_card", "discount": 0, "note": ""}},
        # 跨境订单 — (触发 CROSS_BORDER_AMOUNT)
        {"event_type": "order_pay", "source_id": "WEB-004", "user_id": "U60001", "order_id": "ORD-008",
         "event_payload_json": {"amount": 8000, "item_count": 2, "payment_method": "credit_card", "discount": 200, "is_cross_border": True, "note": ""}},
    ]

    db = SessionLocal()
    try:
        for e in events:
            db.add(RiskEvent(**e))
        db.commit()
        print(f"✅ 已插入 {len(events)} 条演示事件")
    finally:
        db.close()


if __name__ == "__main__":
    # 确保表已创建
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    print("=" * 50)
    print("初始化种子数据...")
    print("=" * 50)
    seed_rules()
    seed_blacklists()
    seed_demo_events()
    print("=" * 50)
    print("种子数据初始化完成！")
    print("运行: uvicorn app.main:app --reload")
    print("访问: http://127.0.0.1:8000")
