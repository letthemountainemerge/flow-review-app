"""
Pydantic 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ========== 文档解析相关 ==========

class Section(BaseModel):
    """文档章节"""
    title: str
    level: int  # 标题层级 1-6
    content: str
    anchor: Optional[str] = None  # 章节锚点


class Role(BaseModel):
    """角色"""
    name: str
    duty: Optional[str] = None


class Activity(BaseModel):
    """活动"""
    name: str
    role: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    description: Optional[str] = None


class Risk(BaseModel):
    """风险"""
    name: str
    control_measure: Optional[str] = None
    is_kcp: bool = False


class KPI(BaseModel):
    """绩效指标"""
    name: str
    target_value: Optional[str] = None
    calculation: Optional[str] = None


class FlowNode(BaseModel):
    """流程图节点"""
    id: str
    name: str
    node_type: str  # startEvent, endEvent, task, exclusiveGateway, parallelGateway, etc.
    lane_id: Optional[str] = None
    outgoing: List[str] = Field(default_factory=list)
    incoming: List[str] = Field(default_factory=list)
    is_kcp: bool = False
    documentation: str = ""


class FlowEdge(BaseModel):
    """流程图连线"""
    id: str
    source: str
    target: str
    name: Optional[str] = None  # 条件标签


class Swimlane(BaseModel):
    """泳道"""
    id: str
    name: str
    node_ids: List[str] = Field(default_factory=list)


class FormField(BaseModel):
    """表单字段"""
    name: str
    field_type: Optional[str] = None
    description: Optional[str] = None


class ParseError(BaseModel):
    """解析错误"""
    type: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class ParsedDocument(BaseModel):
    """解析后的统一文档结构"""
    file_type: str
    file_name: str
    sections: List[Section] = Field(default_factory=list)
    role_table: List[Role] = Field(default_factory=list)
    activity_table: List[Activity] = Field(default_factory=list)
    risk_table: List[Risk] = Field(default_factory=list)
    kpi_table: List[KPI] = Field(default_factory=list)
    nodes: List[FlowNode] = Field(default_factory=list)
    edges: List[FlowEdge] = Field(default_factory=list)
    swimlanes: List[Swimlane] = Field(default_factory=list)
    kcp_nodes: List[str] = Field(default_factory=list)
    form_fields: List[FormField] = Field(default_factory=list)
    full_text: str = ""
    warnings: List[str] = Field(default_factory=list)
    errors: List[ParseError] = Field(default_factory=list)


# ========== 评审相关 ==========

class FindingLocation(BaseModel):
    """问题定位"""
    document_type: str = ""  # "说明书" / "流程图" / "表单"
    section: Optional[str] = None
    page: Optional[int] = None
    node_id: Optional[str] = None
    field_name: Optional[str] = None
    line_number: Optional[int] = None
    quote: str = ""


class Finding(BaseModel):
    """评审发现项"""
    finding_id: str
    severity: str  # "严重" / "一般" / "建议"
    description: str
    location: FindingLocation = Field(default_factory=FindingLocation)
    evidence: str = ""
    suggestion: str = ""
    confidence: float = 1.0


class DimensionResult(BaseModel):
    """单个维度的评审结果"""
    dimension_id: int
    dimension_name: str
    conclusion: str  # "通过" / "不通过" / "需关注"
    score: int  # 0-100
    findings: List[Finding] = Field(default_factory=list)


class ReviewReport(BaseModel):
    """评审报告"""
    task_id: str
    overall_conclusion: str = ""  # "通过" / "不通过" / "需关注"
    overall_score: int = 0
    dimension_results: List[DimensionResult] = Field(default_factory=list)
    summary: str = ""


# ========== 任务相关 ==========

class TaskResponse(BaseModel):
    """任务响应"""
    id: str
    name: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    manual_file: Optional[str] = None
    diagram_file: Optional[str] = None
    form_file: Optional[str] = None
    requirement_file: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int


class FeedbackRequest(BaseModel):
    """专家反馈请求"""
    finding_id: str
    correction_type: str  # false_positive / false_negative / severity_wrong
    expert_comment: str = ""
    expert_conclusion: str = ""


class FeedbackResponse(BaseModel):
    """专家反馈响应"""
    id: str
    task_id: str
    finding_id: str
    correction_type: str
    expert_comment: str
    expert_conclusion: str
    corrected_at: Optional[str] = None


# ========== 知识库相关 ==========

class KnowledgeDocResponse(BaseModel):
    """知识库文档响应"""
    id: str
    title: str
    doc_type: str
    file_path: str
    chunk_count: int
    uploaded_at: Optional[str] = None


class KnowledgeListResponse(BaseModel):
    """知识库文档列表响应"""
    documents: List[KnowledgeDocResponse]
    total: int


# ========== 评审标准结构化展示 ==========

class StandardRuleItem(BaseModel):
    """评审标准单条规则"""
    index: str  # 编号，如 "1.1.1"
    content: str


class StandardSectionItem(BaseModel):
    """评审标准章节"""
    title: str
    rules: List[StandardRuleItem] = Field(default_factory=list)


class StandardCategoryItem(BaseModel):
    """评审标准分类"""
    title: str
    sections: List[StandardSectionItem] = Field(default_factory=list)


class StandardsContentResponse(BaseModel):
    """评审标准结构化内容响应"""
    title: str
    source_count: int
    categories: List[StandardCategoryItem] = Field(default_factory=list)
