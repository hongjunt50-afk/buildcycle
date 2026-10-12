"""SQLAlchemy 数据模型 — 完整版（含P1新增表）"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


# ── 模块1：需求与策划 ──────────────────────────────────────────

class ProjectRequirement(Base):
    """业主需求说明书"""
    __tablename__ = "project_requirement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200), nullable=False, comment="项目名称")
    owner_name = Column(String(100), comment="业主名称")
    requirement_desc = Column(Text, comment="需求描述")
    functional_reqs = Column(Text, comment="功能需求")
    delivery_standard = Column(Text, comment="交付标准")
    budget_limit = Column(Float, comment="预算上限（万元）")
    status = Column(String(20), default="draft", comment="状态: draft/confirmed")
    signed_at = Column(DateTime, comment="签字确认时间")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class FeasibilityAssessment(Base):
    """可行性评估"""
    __tablename__ = "feasibility_assessment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(Integer, ForeignKey("project_requirement.id"))
    land_condition = Column(Text, comment="用地条件")
    planning_indicators = Column(Text, comment="规划指标")
    municipal_conditions = Column(Text, comment="市政配套条件")
    risk_tags = Column(Text, comment="风险标签（逗号分隔）")
    risk_analysis = Column(Text, comment="风险分析详细描述")
    is_feasible = Column(Boolean, default=True, comment="是否可行")
    created_at = Column(DateTime, default=datetime.now)

    requirement = relationship("ProjectRequirement", backref="assessments")


class ProjectPlan(Base):
    """项目策划书"""
    __tablename__ = "project_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requirement_id = Column(Integer, ForeignKey("project_requirement.id"))
    plan_content = Column(Text, comment="策划内容")
    quality_target = Column(String(500), comment="质量目标")
    progress_target = Column(String(500), comment="进度目标")
    cost_target = Column(String(500), comment="成本目标")
    safety_target = Column(String(500), comment="安全目标")
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=datetime.now)

    requirement = relationship("ProjectRequirement", backref="plans")


# ── 模块2：招投标前期 ──────────────────────────────────────────

class BidDueDiligence(Base):
    """项目尽调台账"""
    __tablename__ = "bid_due_diligence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    owner_name = Column(String(100))
    owner_credit = Column(Text, comment="业主资信情况")
    compliance_check = Column(Text, comment="合规性检查")
    fund_source = Column(Text, comment="资金来源")
    risk_notes = Column(Text, comment="风险备注")
    created_at = Column(DateTime, default=datetime.now)


class Contract(Base):
    """合同归档"""
    __tablename__ = "contract"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    contract_no = Column(String(100), comment="合同编号")
    contract_type = Column(String(50), comment="合同类型")
    contract_amount = Column(Float, default=0.0, comment="合同金额（元），签证批准后自动联动")
    schedule_days = Column(Integer, default=0, comment="合同工期（天），签证批准后自动联动")
    content = Column(Text, comment="合同内容/条款")
    risk_tags = Column(Text, comment="AI识别风险标签")
    risk_warnings = Column(Text, comment="风险预警说明")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)


# ── BOQ 工程量清单（P1 新增，来自 OpenConstructionERP） ──────────

class BoqSection(Base):
    """BOQ清单章节"""
    __tablename__ = "boq_section"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200), nullable=False)
    section_code = Column(String(50), comment="章节编号（如 01.01）")
    section_name = Column(String(200), nullable=False, comment="章节名称")
    parent_id = Column(Integer, ForeignKey("boq_section.id"), nullable=True, comment="父章节")
    sort_order = Column(Integer, default=0)
    subtotal = Column(Float, default=0.0, comment="章节小计")
    created_at = Column(DateTime, default=datetime.now)

    children = relationship("BoqSection", backref="parent", remote_side=[id])


class BoqItem(Base):
    """BOQ清单条目"""
    __tablename__ = "boq_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("boq_section.id"), nullable=False)
    item_code = Column(String(50), comment="清单编号")
    item_name = Column(String(300), nullable=False, comment="清单名称")
    unit = Column(String(20), comment="单位（m²/m³/个/项/...）")
    quantity = Column(Float, default=0.0, comment="数量")
    unit_price = Column(Float, default=0.0, comment="单价（元）")
    total_price = Column(Float, default=0.0, comment="合价（元）")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    section = relationship("BoqSection", backref="items")


# ── 模块3：施工实施 ──────────────────────────────────────────

class ProjectTeam(Base):
    """项目部"""
    __tablename__ = "project_team"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    member_name = Column(String(100))
    role = Column(String(50), comment="岗位")
    certificate = Column(String(100), comment="资质证书")
    joined_at = Column(DateTime, default=datetime.now)


class ProgressPlan(Base):
    """进度计划"""
    __tablename__ = "progress_plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    task_name = Column(String(200))
    planned_start = Column(DateTime)
    planned_end = Column(DateTime)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    progress_pct = Column(Float, default=0.0, comment="完成百分比")
    status = Column(String(20), default="pending")
    delay_days = Column(Integer, default=0, comment="滞后天数")
    created_at = Column(DateTime, default=datetime.now)


class TaskDependency(Base):
    """任务依赖关系（P1 新增，来自 CPM-SaaS）"""
    __tablename__ = "task_dependency"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    predecessor_id = Column(Integer, ForeignKey("progress_plan.id"), nullable=False, comment="前置任务")
    successor_id = Column(Integer, ForeignKey("progress_plan.id"), nullable=False, comment="后置任务")
    dep_type = Column(String(10), default="FS", comment="依赖类型: FS/SS/FF/SF")
    lag_days = Column(Integer, default=0, comment="滞后天数")


class QualityCheck(Base):
    """质量三检记录"""
    __tablename__ = "quality_check"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    check_type = Column(String(20), comment="自检/互检/交接检")
    check_item = Column(String(200))
    check_result = Column(String(20), comment="合格/不合格")
    inspector = Column(String(100))
    check_date = Column(DateTime, default=datetime.now)
    remark = Column(Text)


class SafetyCheck(Base):
    """安全检查记录"""
    __tablename__ = "safety_check"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    hazard_item = Column(String(200), comment="隐患项")
    hazard_level = Column(String(20), comment="严重/一般")
    rectification = Column(Text, comment="整改要求")
    status = Column(String(20), default="open", comment="open/closed")
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ChangeOrder(Base):
    """变更签证（P1 增强为自动化工作流）"""
    __tablename__ = "change_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    change_desc = Column(Text, comment="变更描述")
    reason = Column(Text, comment="变更原因")
    amount_change = Column(Float, comment="金额变化（万元）")
    days_change = Column(Integer, comment="工期变化（天）")
    contract_id = Column(Integer, comment="关联合同ID（批准后联动该合同金额/工期）")
    attachments = Column(Text, comment="附件路径")
    workflow_step = Column(String(30), default="initiated",
        comment="工作流步骤: initiated/first_review/second_review/confirmed/archived")
    status = Column(String(20), default="pending", comment="pending/approved/rejected")
    applicant = Column(String(100))
    reviewer = Column(String(100), nullable=True)
    ai_confidence = Column(String(10), comment="AI置信度: 高/中/低")
    verify_result = Column(Text, comment="二次验算结果JSON")
    created_at = Column(DateTime, default=datetime.now)
    reviewed_at = Column(DateTime, nullable=True)


class ConstructionDoc(Base):
    """施工资料（同步管理 + 流向数据校验）"""
    __tablename__ = "construction_doc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    doc_type = Column(String(50), comment="施工日志/技术交底/隐蔽验收/...")
    content = Column(Text)
    related_date = Column(DateTime, comment="关联施工日期")
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(100), comment="提交人")
    is_synced = Column(Boolean, default=True, comment="是否同步录入")
    validation_status = Column(String(20), default="pending", comment="校验状态: pending/passed/failed")
    validation_errors = Column(Text, comment="校验错误信息")


# ── 模块4：竣工结算与维保 ──────────────────────────────────────

class CompletionIssue(Base):
    """竣工验收整改问题"""
    __tablename__ = "completion_issue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    issue_desc = Column(Text)
    responsible_person = Column(String(100))
    severity = Column(String(20), default="一般", comment="严重/一般/危急")
    status = Column(String(20), default="open")
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(100), comment="提交人")
    attachments = Column(Text, comment="整改前后照片路径")


class Settlement(Base):
    """结算对账记录"""
    __tablename__ = "settlement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    contract_amount = Column(Float)
    change_amount = Column(Float, default=0)
    settlement_amount = Column(Float, nullable=True)
    audit_amount = Column(Float, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now)


class WarrantyWorkOrder(Base):
    """质保报修工单"""
    __tablename__ = "warranty_work_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    reporter = Column(String(100), comment="报修人")
    issue_desc = Column(Text)
    assignee = Column(String(100), comment="维修人")
    repair_result = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)


class WarrantyDeposit(Base):
    """质保金跟踪"""
    __tablename__ = "warranty_deposit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(200))
    deposit_amount = Column(Float, comment="质保金金额（万元）")
    expiry_date = Column(DateTime, comment="质保到期日")
    return_amount = Column(Float, nullable=True, comment="已退还金额")
    status = Column(String(20), default="pending", comment="pending/returned/deducted")
    created_at = Column(DateTime, default=datetime.now)


# ── 全局通用表（P1 新增） ──────────────────────────────────────

class AuditLog(Base):
    """审计日志（来源 EvoFlow 流向数据校验）"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), comment="操作表")
    record_id = Column(Integer, comment="记录ID")
    action = Column(String(20), comment="create/update/delete/verify")
    operator = Column(String(100), comment="操作人")
    old_value = Column(Text, comment="修改前值（JSON）")
    new_value = Column(Text, comment="修改后值（JSON）")
    detail = Column(Text, comment="操作详情")
    created_at = Column(DateTime, default=datetime.now)


class WorkflowDefinition(Base):
    """工作流定义（来源 EvoFlow 工作流自动化）"""
    __tablename__ = "workflow_definition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="工作流名称")
    biz_type = Column(String(50), nullable=False, comment="业务类型: change_order/quality/safety/...")
    steps = Column(Text, comment="步骤定义（JSON数组）")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class WorkflowInstance(Base):
    """工作流实例"""
    __tablename__ = "workflow_instance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_def_id = Column(Integer, ForeignKey("workflow_definition.id"))
    biz_type = Column(String(50), comment="业务类型")
    biz_record_id = Column(Integer, comment="关联业务记录ID")
    current_step = Column(String(50), comment="当前步骤")
    current_step_index = Column(Integer, default=0)
    status = Column(String(20), default="running", comment="running/completed/rejected/paused")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

    definition = relationship("WorkflowDefinition", backref="instances")


class WorkflowStepLog(Base):
    """工作流步骤日志"""
    __tablename__ = "workflow_step_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("workflow_instance.id"))
    step_name = Column(String(50))
    step_index = Column(Integer)
    action = Column(String(20), comment="auto/manual/verify_failed")
    result = Column(Text, comment="步骤结果JSON")
    operator = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    instance = relationship("WorkflowInstance", backref="step_logs")


class KnowledgeSource(Base):
    """知识源（P1 新增，前端可上传）"""
    __tablename__ = "knowledge_source"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    source_type = Column(String(30), default="manual",
        comment="manual/file_upload/web_search")
    file_path = Column(String(500), nullable=True, comment="上传文件路径")
    content = Column(Text, comment="原始内容")
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
