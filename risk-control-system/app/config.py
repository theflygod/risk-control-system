"""存放系统的所有配置常量，包括数据库路径、风险阈值、黑名单类型、事件类型枚举等，所有模块引用同一份配置。"""

import os

# 数据库 - SQLite 文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, '..', 'risk_control.db')}"

# 业务事件类型
EVENT_TYPES = ["order_create", "order_pay", "after_sale_apply", "logistics_complaint"]

# 风险等级
RISK_LEVELS = ["low", "medium", "high"]

# 处理建议
DECISIONS = ["pass", "manual_review", "reject"]

# 案件状态
CASE_STATUSES = ["pending", "reviewing", "approved", "rejected", "resolved"]

# 风险评分阈值
SCORE_LOW_MAX = 30        # 0-30: 低风险
SCORE_MEDIUM_MAX = 60     # 31-60: 中风险
                          # 61-100: 高风险

# 黑名单类型
BLACKLIST_TYPES = ["user_id", "ip_address", "device_id", "address_keyword"]

# 规则状态
RULE_STATUSES = ["enabled", "disabled"]

# 评估状态
ASSESSMENT_STATUSES = ["running", "completed", "failed"]
