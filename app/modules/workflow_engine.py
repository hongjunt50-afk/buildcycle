"""工作流自动化引擎（来源 EvoFlow 方法论 + Massing 模块思想）"""

import json
from datetime import datetime
from typing import Optional, List, Dict

from app.database.connection import DatabaseManager
from app.database.models import (
    WorkflowDefinition, WorkflowInstance, WorkflowStepLog, AuditLog,
    ChangeOrder, Contract
)


class WorkflowEngine:
    """
    工作流自动化引擎
    每个业务模块是一个可配置的工作流，支持自动步骤和人工步骤混合编排
    """

    def __init__(self):
        self.db = DatabaseManager()

    # ── 工作流定义 ──

    def create_workflow(self, name: str, biz_type: str, steps: List[Dict]) -> int:
        """创建工作流定义
        steps: [
            {"name": "步骤名", "type": "auto/manual", "action": "动作名", "verify": "验算类型/None"},
            ...
        ]
        """
        session = self.db.get_session()
        try:
            wf = WorkflowDefinition(
                name=name,
                biz_type=biz_type,
                steps=json.dumps(steps, ensure_ascii=False),
            )
            session.add(wf)
            session.commit()
            return wf.id
        finally:
            session.close()

    def get_workflow(self, biz_type: str) -> Optional[Dict]:
        """获取业务类型对应的活跃工作流"""
        session = self.db.get_session()
        try:
            wf = session.query(WorkflowDefinition).filter(
                WorkflowDefinition.biz_type == biz_type,
                WorkflowDefinition.is_active == True
            ).first()
            if wf:
                return {
                    "id": wf.id,
                    "name": wf.name,
                    "biz_type": wf.biz_type,
                    "steps": json.loads(wf.steps),
                }
            return None
        finally:
            session.close()

    # ── 工作流实例 ──

    def start_instance(self, biz_type: str, biz_record_id: int) -> int:
        """启动工作流实例"""
        wf = self.get_workflow(biz_type)
        if not wf:
            raise ValueError(f"未找到{biz_type}的工作流定义")

        session = self.db.get_session()
        try:
            instance = WorkflowInstance(
                workflow_def_id=wf["id"],
                biz_type=biz_type,
                biz_record_id=biz_record_id,
                current_step=wf["steps"][0]["name"] if wf["steps"] else "",
                current_step_index=0,
                status="running",
            )
            session.add(instance)
            session.commit()

            # 记录第一步
            self._log_step(session, instance.id, 0, wf["steps"][0]["name"], "auto", "工作流启动")

            return instance.id
        finally:
            session.close()

    def advance(self, instance_id: int, operator: str = "AI",
                result: str = "auto_passed", detail: str = "") -> Dict:
        """推进工作流到下一步"""
        session = self.db.get_session()
        try:
            instance = session.query(WorkflowInstance).get(instance_id)
            if not instance:
                return {"status": "error", "message": "工作流实例不存在"}

            if instance.status != "running":
                return {"status": "error", "message": f"工作流已{instance.status}"}

            wf = session.query(WorkflowDefinition).get(instance.workflow_def_id)
            steps = json.loads(wf.steps)

            # 记录当前步骤结果
            self._log_step(session, instance_id, instance.current_step_index,
                          instance.current_step, "auto" if operator == "AI" else "manual",
                          detail or result)

            # 推进到下一步
            next_index = instance.current_step_index + 1
            if next_index >= len(steps):
                instance.status = "completed"
                instance.completed_at = datetime.now()
                # 批准完成 → 账务联动（签证批准后合同金额/工期自动更新）
                if instance.biz_type == "change_order":
                    self._apply_change_order_effects(session, instance.biz_record_id)
                session.commit()
                return {
                    "status": "completed",
                    "message": "工作流已完成",
                    "total_steps": len(steps),
                }

            instance.current_step_index = next_index
            instance.current_step = steps[next_index]["name"]
            session.commit()

            return {
                "status": "running",
                "current_step": instance.current_step,
                "current_step_index": next_index,
                "total_steps": len(steps),
                "step_type": steps[next_index].get("type", "auto"),
            }
        finally:
            session.close()

    def reject(self, instance_id: int, reason: str = ""):
        """驳回工作流"""
        session = self.db.get_session()
        try:
            instance = session.query(WorkflowInstance).get(instance_id)
            if instance:
                instance.status = "rejected"
                # 驳回也要在业务记录上留痕（DL-20260914-002 R2）
                if instance.biz_type == "change_order":
                    co = session.query(ChangeOrder).get(instance.biz_record_id)
                    if co:
                        co.status = "rejected"
                        co.workflow_step = "rejected"
                        co.reviewed_at = datetime.now()
                session.commit()
        finally:
            session.close()

    # ── 账务联动（Test-King M5-CO-001 实战发现的缺口）──────────────

    def _apply_change_order_effects(self, session, biz_record_id: int):
        """签证批准完成 → 合同金额/工期联动。

        行业硬规则（DL-20260914-002）：先批后干、批准即联动、幂等防重。
        amount_change 单位是万元，合同金额单位是元。
        """
        co = session.query(ChangeOrder).get(biz_record_id)
        if not co:
            return
        if co.status == "approved":
            return  # 幂等：已联动过，不重复加

        co.status = "approved"
        co.workflow_step = "archived"
        co.reviewed_at = datetime.now()

        if not co.contract_id:
            return  # 没有关联合同（旧数据/无合同），只改状态

        contract = session.query(Contract).get(co.contract_id)
        if not contract:
            return

        amount_yuan = float(co.amount_change or 0) * 10000.0
        days = int(co.days_change or 0)
        before_amount, before_days = contract.contract_amount or 0.0, contract.schedule_days or 0
        contract.contract_amount = before_amount + amount_yuan
        contract.schedule_days = before_days + days

        self.log_audit("contract", contract.id, "change_order_applied",
                       operator="system",
                       detail=(f"签证#{co.id} 批准联动: 金额{before_amount:.2f}→"
                               f"{contract.contract_amount:.2f}元, "
                               f"工期{before_days}→{contract.schedule_days}天"))

    def _log_step(self, session, instance_id: int, step_index: int,
                  step_name: str, action: str, result: str):
        """记录工作流步骤日志"""
        log = WorkflowStepLog(
            instance_id=instance_id,
            step_name=step_name,
            step_index=step_index,
            action=action,
            result=result,
            operator="AI" if action == "auto" else None,
        )
        session.add(log)

    # ── 审计日志 ──

    def log_audit(self, table_name: str, record_id: int, action: str,
                  operator: str, old_value: str = "", new_value: str = "", detail: str = ""):
        """记录审计日志"""
        session = self.db.get_session()
        try:
            log = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                operator=operator,
                old_value=old_value,
                new_value=new_value,
                detail=detail,
            )
            session.add(log)
            session.commit()
        finally:
            session.close()

    # ── 变更签证审批流（首个自动化工作流） ──

    def init_change_order_workflow(self):
        """初始化变更签证审批流"""
        steps = [
            {"name": "发起变更", "type": "manual", "action": "submit", "verify": None},
            {"name": "AI初审", "type": "auto", "action": "review", "verify": "amount",
             "note": "AI自动检查变更描述完整性、金额计算、二次验算"},
            {"name": "联网市场价格查询", "type": "auto", "action": "web_search",
             "note": "联网查询四川地区同类变更市场价格"},
            {"name": "复审汇总", "type": "manual", "action": "second_review",
             "note": "人工审核AI初审结果和联网查询数据"},
            {"name": "确认归档", "type": "manual", "action": "confirm", "verify": None},
        ]
        return self.create_workflow("变更签证审批流", "change_order", steps)

    def init_quality_workflow(self):
        """初始化质量整改闭环工作流"""
        steps = [
            {"name": "问题登记", "type": "manual", "action": "report"},
            {"name": "AI分类", "type": "auto", "action": "classify",
             "note": "AI自动分类问题严重程度（一般/严重/危急）"},
            {"name": "整改派发", "type": "auto", "action": "assign",
             "note": "AI根据问题类型自动派发到对应责任人"},
            {"name": "整改完成", "type": "manual", "action": "fix"},
            {"name": "AI复查", "type": "auto", "action": "verify", "verify": "quality",
             "note": "AI检查整改结果是否满足要求"},
            {"name": "关闭归档", "type": "manual", "action": "close"},
        ]
        return self.create_workflow("质量整改闭环", "quality", steps)


# 全局实例
workflow = WorkflowEngine()
