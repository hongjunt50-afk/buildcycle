"""合同风险识别 Agent"""

import json
import re


class RiskAnalyzer:
    """合同风险识别与分析"""

    RISK_KEYWORDS = {
        "霸王条款": [
            "最终解释权", "单方调整", "单方变更", "无条件",
            "概不负责", "不承担任何责任", "免除己方责任",
            "不可撤销", "不得异议",
        ],
        "付款风险": [
            "无预付款", "垫资", "延期付款", "滞后支付",
            "无息", "不支付利息", "背靠背",
        ],
        "工期风险": [
            "无条件赶工", "不合理工期", "工期不调整",
            "逾期罚款", "高额违约金", "每日千分之",
        ],
        "责任转移": [
            "乙方承担全部", "乙方独立承担", "转移风险",
            "不可抗力由乙方", "第三方责任由乙方",
        ],
    }

    def analyze(self, contract_text: str) -> dict:
        """分析合同文本，返回风险标签和说明"""
        if not contract_text:
            return {"tags": [], "warnings": [], "risk_level": "低"}

        tags = []
        warnings = []

        for category, keywords in self.RISK_KEYWORDS.items():
            found = [kw for kw in keywords if kw in contract_text]
            if found:
                tags.append(category)
                warnings.append(f"发现{category}：{', '.join(found)}")

        return {
            "tags": tags,
            "warnings": warnings,
            "risk_level": "高" if len(tags) >= 3 else ("中" if tags else "低"),
        }


if __name__ == "__main__":
    # 测试
    text = "甲方拥有最终解释权，乙方不得异议。如工期延误，乙方承担每日千分之五的违约金。"
    result = RiskAnalyzer().analyze(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
