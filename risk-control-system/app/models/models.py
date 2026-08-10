"""实现数据表的要求:8 张数据表的 SQLAlchemy ORM 模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class RiskEvent(Base):
    """风险事件表 — 记录每次风险检查的原始入参"""
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(32), nullable=False, comment="事件类型: order_create/order_pay/after_sale_apply/logistics_complaint")
    source_id = Column(String(64), nullable=False, comment="来源唯一标识")
    user_id = Column(String(64), nullable=False, comment="用户编号")
    order_id = Column(String(64), nullable=True, comment="订单编号")
    event_payload_json = Column(JSON, nullable=True, comment="事件原始数据")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    assessment = relationship("RiskAssessment", back_populates="event", uselist=False)


class RiskAssessment(Base):
    """风险评估表 — 记录每次评估的评分、等级和处理建议"""
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("risk_events.id"), nullable=False, comment="关联事件ID")
    risk_score = Column(Integer, nullable=False, comment="风险评分 0-100")
    risk_level = Column(String(16), nullable=False, comment="风险等级: low/medium/high")
    decision = Column(String(16), nullable=False, comment="处理建议: pass/manual_review/reject")
    assessment_status = Column(String(16), default="completed", comment="评估状态")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    event = relationship("RiskEvent", back_populates="assessment")
    feature_snapshot = relationship("FeatureSnapshot", back_populates="assessment", uselist=False)
    rule_hits = relationship("RuleHit", back_populates="assessment")
    risk_case = relationship("RiskCase", back_populates="assessment", uselist=False)


class FeatureSnapshot(Base):
    """特征快照表 — 记录评估时的所有特征值，键值对保存"""
    __tablename__ = "feature_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("risk_assessments.id"), nullable=False, comment="关联评估ID")
    feature_json = Column(JSON, nullable=False, comment="特征快照，键值对")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    assessment = relationship("RiskAssessment", back_populates="feature_snapshot")


class RiskRule(Base):
    """风险规则表 — 规则元信息和JSON条件"""
    __tablename__ = "risk_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_code = Column(String(64), unique=True, nullable=False, comment="规则编码")
    rule_name = Column(String(128), nullable=False, comment="规则名称")
    rule_status = Column(String(16), default="enabled", comment="规则状态: enabled/disabled")
    priority = Column(Integer, default=0, comment="优先级，数值越大越优先")
    score = Column(Integer, default=10, comment="命中分值")
    condition_json = Column(JSON, nullable=False, comment="规则条件JSON，支持 and/or/比较运算符")
    description = Column(String(256), nullable=True, comment="命中描述")
    hit_count = Column(Integer, default=0, comment="命中次数统计")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    rule_hits = relationship("RuleHit", back_populates="rule")


class RuleHit(Base):
    """规则命中记录表 — 记录每次评估命中了哪些规则"""
    __tablename__ = "rule_hits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("risk_assessments.id"), nullable=False, comment="关联评估ID")
    rule_id = Column(Integer, ForeignKey("risk_rules.id"), nullable=False, comment="关联规则ID")
    hit_score = Column(Integer, nullable=False, comment="实际命中分值")
    hit_message = Column(String(256), nullable=True, comment="命中原因")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    assessment = relationship("RiskAssessment", back_populates="rule_hits")
    rule = relationship("RiskRule", back_populates="rule_hits")


class RiskCase(Base):
    """风险案件表 — 高风险事件自动创建的审核案件"""
    __tablename__ = "risk_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("risk_assessments.id"), nullable=False, comment="关联评估ID")
    user_id = Column(String(64), nullable=False, comment="关联用户")
    order_id = Column(String(64), nullable=True, comment="关联订单")
    case_status = Column(String(16), default="pending", comment="案件状态: pending/reviewing/approved/rejected/resolved")
    reviewer_id = Column(String(64), nullable=True, comment="审核人ID")
    review_result = Column(String(16), nullable=True, comment="审核结果")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    assessment = relationship("RiskAssessment", back_populates="risk_case")
    review_logs = relationship("ReviewLog", back_populates="case")


class Blacklist(Base):
    """黑名单表 — 支持用户/IP/设备/地址关键词"""
    __tablename__ = "blacklists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    blacklist_type = Column(String(32), nullable=False, comment="类型: user_id/ip_address/device_id/address_keyword")
    blacklist_value = Column(String(256), nullable=False, comment="命中值")
    remark = Column(String(256), nullable=True, comment="备注")
    status = Column(String(16), default="active", comment="状态: active/inactive")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class ReviewLog(Base):
    """审核日志表 — 记录案件每次审核操作"""
    __tablename__ = "review_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("risk_cases.id"), nullable=False, comment="关联案件ID")
    operator_id = Column(String(64), nullable=False, comment="操作人ID")
    action_type = Column(String(32), nullable=False, comment="操作类型: approve/reject/comment")
    action_remark = Column(String(512), nullable=True, comment="操作备注")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    case = relationship("RiskCase", back_populates="review_logs")
