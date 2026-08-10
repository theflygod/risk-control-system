"""
Pydantic 请求/响应模型 — 15 个 API 接口的入参校验和出参格式化
定义所有 API 接口的请求体和响应体结构,FastAPI 用它们自动校验入参、生成 API 文档。包含：

请求 schema：RiskCheckRequest（事件检查）、RuleCreate/Update（规则管理）、CaseReview（案件审核）等
响应 schema：RiskCheckResponse（评分+等级+命中规则+特征快照）、DashboardStats（看板统计）等
"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============ 风险检查 ============

class RiskCheckRequest(BaseModel):
    """发起风险检查的请求体"""
    event_type: str = Field(..., description="事件类型: order_create/order_pay/after_sale_apply/logistics_complaint")
    source_id: str = Field(..., description="来源唯一标识")
    user_id: str = Field(..., description="用户编号")
    order_id: Optional[str] = Field(None, description="订单编号")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "order_create",
                "source_id": "SRC-20240801-001",
                "user_id": "U10001",
                "order_id": "ORD-20240801-001"
            }
        }


class RuleHitItem(BaseModel):
    """命中的单条规则"""
    rule_name: str
    rule_code: str
    hit_score: int
    hit_message: str


class RiskCheckResponse(BaseModel):
    """风险检查的完整响应"""
    assessment_id: int
    risk_score: int = Field(..., description="风险评分 0-100")
    risk_level: str = Field(..., description="风险等级: low/medium/high")
    decision: str = Field(..., description="处理建议: pass/manual_review/reject")
    rule_hits: List[RuleHitItem] = Field(default_factory=list, description="命中的规则列表")
    feature_snapshot: dict = Field(default_factory=dict, description="特征快照，键值对")
    case_id: Optional[int] = Field(None, description="自动创建的案件ID（如有）")


# ============ 规则管理 ============

class RuleCreate(BaseModel):
    """新增规则"""
    rule_code: str = Field(..., description="规则编码，唯一")
    rule_name: str = Field(..., description="规则名称")
    rule_status: str = Field(default="enabled", description="规则状态: enabled/disabled")
    priority: int = Field(default=0, description="优先级")
    score: int = Field(default=10, description="命中分值")
    condition_json: dict = Field(..., description="规则条件JSON")
    description: str = Field(default="", description="命中描述")


class RuleUpdate(BaseModel):
    """更新规则"""
    rule_name: Optional[str] = None
    rule_status: Optional[str] = None
    priority: Optional[int] = None
    score: Optional[int] = None
    condition_json: Optional[dict] = None
    description: Optional[str] = None


class RuleStatusToggle(BaseModel):
    """启停用规则"""
    rule_status: str = Field(..., description="目标状态: enabled/disabled")


class RuleDelete(BaseModel):
    """删除规则（可批量）"""
    rule_ids: List[int] = Field(..., description="要删除的规则ID列表")


# ============ 案件管理 ============

class CaseReview(BaseModel):
    """审核案件"""
    case_id: int = Field(..., description="案件ID")
    review_result: str = Field(..., description="审核结果: approved/rejected")
    review_remark: Optional[str] = Field(None, description="审核备注")


class CaseListItem(BaseModel):
    """案件列表项"""
    case_id: int
    case_status: str
    risk_level: str
    risk_score: int
    user_id: str
    order_id: Optional[str]
    reviewer_id: Optional[str]
    review_result: Optional[str]
    created_at: str


class CaseDetail(BaseModel):
    """案件详情 — 包含评估结果、命中规则、特征快照、审核日志"""
    case_id: int
    case_status: str
    review_result: Optional[str]
    reviewer_id: Optional[str]
    user_id: str
    order_id: Optional[str]
    assessment: dict = Field(default_factory=dict, description="评估结果（评分/等级/建议）")
    rule_hits: List[RuleHitItem] = Field(default_factory=list, description="命中规则")
    feature_snapshot: dict = Field(default_factory=dict, description="特征快照")
    review_logs: List[dict] = Field(default_factory=list, description="审核日志")


# ============ 黑名单管理 ============

class BlacklistCreate(BaseModel):
    """新增黑名单"""
    blacklist_type: str = Field(..., description="类型: user_id/ip_address/device_id/address_keyword")
    blacklist_value: str = Field(..., description="命中值")
    remark: Optional[str] = Field(None, description="备注")


class BlacklistDelete(BaseModel):
    """删除黑名单"""
    blacklist_ids: List[int] = Field(..., description="要删除的黑名单ID列表")


# ============ 用户画像 ============

class UserProfile(BaseModel):
    """用户画像"""
    user_id: str
    history_order_count: int = 0
    refund_count: int = 0
    complaint_count: int = 0
    address_count: int = 0
    recent_risk_events: List[dict] = Field(default_factory=list)
    related_cases: List[dict] = Field(default_factory=list)


# ============ 运营看板 ============

class DashboardStats(BaseModel):
    """看板统计数据"""
    total_events: int = Field(..., description="风险事件总数")
    high_risk_ratio: float = Field(..., description="高风险占比")
    case_pending_count: int = Field(..., description="待审核案件数")
    case_approved_count: int = Field(..., description="已通过案件数")
    rule_hit_ranking: List[dict] = Field(default_factory=list, description="规则命中排行")
    risk_level_distribution: dict = Field(default_factory=dict, description="风险等级分布 {low: N, medium: N, high: N}")
    blacklist_hit_count: int = Field(..., description="黑名单命中次数")
    recent_events: List[dict] = Field(default_factory=list, description="最近风险事件")


# ============ 通用 ============

class MessageResponse(BaseModel):
    """通用消息响应"""
    status: str = "ok"
    message: str = "操作成功"
