"""资料合规校验 Agent"""

from datetime import datetime


class DocValidator:
    """施工资料合规校验"""

    def __init__(self):
        self.checks = []

    def validate_construction_doc(self, doc_type: str, content: str, related_date: str) -> list:
        """校验单份施工资料的合规性"""
        issues = []

        # 内容不能为空
        if not content or not content.strip():
            issues.append("内容为空")

        # 资料类型必须填写
        if not doc_type:
            issues.append("资料类型未填写")

        # 关联日期不能晚于当前时间
        if related_date:
            try:
                dt = datetime.strptime(related_date, "%Y-%m-%d")
                if dt > datetime.now():
                    issues.append("关联施工日期不能晚于当前时间")
            except ValueError:
                issues.append("关联施工日期格式错误（应为 YYYY-MM-DD）")

        return issues

    def validate_doc_sequence(self, doc_list: list) -> list:
        """校验多份资料之间的时间逻辑一致性"""
        warnings = []
        sorted_docs = sorted(doc_list, key=lambda x: x.get("date", ""))

        for i in range(len(sorted_docs) - 1):
            curr = sorted_docs[i]
            nxt = sorted_docs[i + 1]

            # 施工日志不应早于技术交底等技术准备资料
            if curr.get("type") == "施工日志" and nxt.get("type") == "技术交底":
                warnings.append(
                    f"施工日志({curr.get('date')})早于技术交底({nxt.get('date')})，逻辑异常"
                )

        return warnings


if __name__ == "__main__":
    v = DocValidator()
    print(v.validate_construction_doc("施工日志", "今日完成桩基施工10根", "2025-01-15"))
