"""Source Matrix 文档来源定义（来自 EvoFlow 方法论）"""

import json
from datetime import datetime
from typing import List, Dict, Optional

from app.database.connection import DatabaseManager


class SourceMatrix:
    """
    Source Matrix（源矩阵）
    定义每个文档/数据的来源、什么算有效、什么算完整
    达到100%就绪时自动标记
    """

    def __init__(self):
        self.db = DatabaseManager()

    # ── 规则定义 ──

    def define_rule(self, doc_type: str, source: str,
                    valid_fields: List[str],
                    required_relations: List[str],
                    completeness_check: str) -> int:
        """定义文档规则
        doc_type: 施工日志/技术交底/隐蔽验收/...
        source: 谁产生的（施工员/质检员/安全员/...）
        valid_fields: 必填字段列表
        required_relations: 关联文档类型列表
        completeness_check: 完整性检查SQL/逻辑描述
        """
        session = self.db.get_session()
        try:
            from app.database.models import KnowledgeSource
            # 暂存规则到knowledge_source
            content = json.dumps({
                "source": source,
                "valid_fields": valid_fields,
                "required_relations": required_relations,
                "completeness_check": completeness_check,
            }, ensure_ascii=False)

            ks = KnowledgeSource(
                name=f"source_matrix:{doc_type}",
                source_type="source_matrix",
                content=content,
            )
            session.add(ks)
            session.commit()
            return ks.id
        finally:
            session.close()

    def get_rule(self, doc_type: str) -> Optional[Dict]:
        """获取文档类型的规则"""
        session = self.db.get_session()
        try:
            from app.database.models import KnowledgeSource
            ks = session.query(KnowledgeSource).filter(
                KnowledgeSource.name == f"source_matrix:{doc_type}"
            ).first()
            if ks:
                return json.loads(ks.content)
            return None
        finally:
            session.close()

    # ── 文档校验 ──

    def validate_document(self, doc_type: str, doc_data: Dict) -> Dict:
        """校验单个文档的有效性"""
        rule = self.get_rule(doc_type)
        if not rule:
            return {"valid": False, "errors": [f"未定义{doc_type}的规则"]}

        errors = []

        # 检查必填字段
        for field in rule.get("valid_fields", []):
            if field not in doc_data or not doc_data[field]:
                errors.append(f"缺少必填字段: {field}")

        # 检查来源
        expected_source = rule.get("source", "")
        actual_source = doc_data.get("created_by", "")
        if expected_source and actual_source and expected_source != actual_source:
            errors.append(f"来源不匹配: 期望{expected_source}，实际{actual_source}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "passed": len(errors) == 0,
            "failed": len(errors) > 0,
        }

    def check_completeness(self, project_name: str, doc_type: str) -> Dict:
        """检查文档完整性（所有关联文档是否齐全）"""
        rule = self.get_rule(doc_type)
        if not rule:
            return {"complete": False, "missing": ["未定义规则"]}

        session = self.db.get_session()
        try:
            from app.database.models import ConstructionDoc

            missing = []
            for rel in rule.get("required_relations", []):
                count = session.query(ConstructionDoc).filter(
                    ConstructionDoc.project_name == project_name,
                    ConstructionDoc.doc_type == rel,
                ).count()
                if count == 0:
                    missing.append(rel)

            return {
                "complete": len(missing) == 0,
                "missing": missing,
                "total_required": len(rule.get("required_relations", [])),
                "existing": len(rule.get("required_relations", [])) - len(missing),
            }
        finally:
            session.close()

    def check_readiness(self, project_name: str, doc_type: str) -> Dict:
        """检查文档就绪状态（完整+有效）"""
        completeness = self.check_completeness(project_name, doc_type)
        readiness_pct = 0
        if completeness["total_required"] > 0:
            readiness_pct = round(completeness["existing"] / completeness["total_required"] * 100, 1)

        return {
            "project": project_name,
            "doc_type": doc_type,
            "readiness_pct": readiness_pct,
            "complete": completeness["complete"],
            "missing": completeness["missing"],
            "status": "就绪" if readiness_pct == 100 else f"进行中({readiness_pct}%)",
        }

    # ── 预设规则 ──

    def init_default_rules(self):
        """初始化默认的 Source Matrix 规则"""
        rules = [
            {
                "doc_type": "施工日志",
                "source": "施工员",
                "valid_fields": ["project_name", "content", "related_date", "created_by"],
                "required_relations": ["技术交底"],
                "completeness_check": "施工日志日期不得早于技术交底日期",
            },
            {
                "doc_type": "技术交底",
                "source": "技术负责人",
                "valid_fields": ["project_name", "content", "related_date"],
                "required_relations": ["施工方案"],
                "completeness_check": "技术交底必须在施工前完成",
            },
            {
                "doc_type": "隐蔽验收",
                "source": "质检员",
                "valid_fields": ["project_name", "content", "related_date", "created_by"],
                "required_relations": ["工序验收", "质量检查"],
                "completeness_check": "隐蔽验收前必须先完成工序验收",
            },
            {
                "doc_type": "变更签证",
                "source": "项目经理",
                "valid_fields": ["project_name", "change_desc", "amount_change"],
                "required_relations": ["合同", "变更令"],
                "completeness_check": "变更签证必须有对应的变更令编号",
            },
        ]
        for rule in rules:
            self.define_rule(**rule)


if __name__ == "__main__":
    sm = SourceMatrix()
    sm.init_default_rules()

    # 测试
    result = sm.validate_document("施工日志", {
        "project_name": "测试项目",
        "content": "今日完成...",
        "related_date": "2026-09-09",
        "created_by": "施工员",
    })
    print(f"校验: {'通过' if result['valid'] else '失败'}")
    if result.get("errors"):
        print(f"  错误: {result['errors']}")

    readiness = sm.check_readiness("测试项目", "隐蔽验收")
    print(f"就绪度: {readiness['readiness_pct']}% - {readiness['status']}")
