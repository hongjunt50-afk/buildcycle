"""挣值管理（EVM）引擎"""

from datetime import date
from typing import List, Dict, Optional


class EVMEngine:
    """
    挣值管理（Earned Value Management）
    跟踪项目的计划值、挣值、实际成本，计算绩效指标
    """

    def __init__(self, project_name: str, budget_at_completion: float):
        self.project_name = project_name
        self.bac = budget_at_completion  # 完工预算
        self.periods: List[Dict] = []  # 各周期数据

    def add_period(self, period_name: str, planned_value: float,
                   earned_value: float, actual_cost: float):
        """添加一个周期的数据"""
        self.periods.append({
            "period": period_name,
            "pv": planned_value,
            "ev": earned_value,
            "ac": actual_cost,
        })

    def calculate(self) -> Dict:
        """计算所有 EVM 指标"""
        if not self.periods:
            return {"error": "没有数据"}

        latest = self.periods[-1]
        pv = latest["pv"]
        ev = latest["ev"]
        ac = latest["ac"]

        # 偏差指标
        sv = ev - pv  # 进度偏差（>0 超前，<0 滞后）
        cv = ev - ac  # 成本偏差（>0 节约，<0 超支）

        # 绩效指数
        spi = ev / pv if pv > 0 else 0  # 进度绩效指数
        cpi = ev / ac if ac > 0 else 0  # 成本绩效指数

        # 预测
        eac = self.bac / cpi if cpi > 0 else 0  # 完工估算
        etc = eac - ac  # 剩余工作估算
        vac = self.bac - eac  # 完工偏差

        # 二次验算
        verify_passed = True
        verify_notes = []

        # 用不同方法验证 SPI
        if len(self.periods) >= 2:
            prev = self.periods[-2]
            prev_spi = prev["ev"] / prev["pv"] if prev["pv"] > 0 else 0
            if abs(spi - prev_spi) > 0.3:
                verify_passed = False
                verify_notes.append(f"SPI从{prev_spi:.2f}跳变到{spi:.2f}，请确认")

        # 验算 BAC 合理性
        total_ev = sum(p["ev"] for p in self.periods)
        if total_ev > self.bac * 1.1:
            verify_passed = False
            verify_notes.append(f"累计挣值({total_ev:.0f})超过BAC({self.bac:.0f})的110%")

        return {
            "project": self.project_name,
            "bac": self.bac,
            "periods": self.periods,
            "latest": {
                "pv": round(pv, 2),
                "ev": round(ev, 2),
                "ac": round(ac, 2),
            },
            "variance": {
                "sv": round(sv, 2),
                "cv": round(cv, 2),
                "sv_pct": round(sv / abs(pv) * 100, 1) if pv != 0 else 0,
                "cv_pct": round(cv / abs(ev) * 100, 1) if ev != 0 else 0,
            },
            "performance": {
                "spi": round(spi, 4),
                "cpi": round(cpi, 4),
                "status": self._status_label(spi, cpi),
            },
            "forecast": {
                "eac": round(eac, 2),
                "etc": round(etc, 2),
                "vac": round(vac, 2),
                "eac_vs_bac": f"{'超支' if eac > self.bac else '节约'}{abs(eac - self.bac):.0f}",
            },
            "verify": {
                "passed": verify_passed,
                "notes": verify_notes,
            },
        }

    def _status_label(self, spi: float, cpi: float) -> str:
        if spi >= 1.0 and cpi >= 1.0:
            return "✅ 进度超前，成本节约"
        elif spi >= 1.0 and cpi < 1.0:
            return "⚠️ 进度超前，成本超支"
        elif spi < 1.0 and cpi >= 1.0:
            return "⚠️ 进度滞后，成本节约"
        else:
            return "🔴 进度滞后，成本超支"


if __name__ == "__main__":
    evm = EVMEngine("示例项目", 1000000)
    evm.add_period("1月", 100000, 80000, 95000)
    evm.add_period("2月", 250000, 220000, 240000)
    evm.add_period("3月", 400000, 380000, 420000)
    evm.add_period("4月", 550000, 520000, 560000)

    result = evm.calculate()
    print(f"项目: {result['project']}")
    print(f"BAC: {result['bac']}")
    print(f"最新: PV={result['latest']['pv']}, EV={result['latest']['ev']}, AC={result['latest']['ac']}")
    print(f"偏差: SV={result['variance']['sv']}, CV={result['variance']['cv']}")
    print(f"绩效: SPI={result['performance']['spi']}, CPI={result['performance']['cpi']}")
    print(f"状态: {result['performance']['status']}")
    print(f"预测: EAC={result['forecast']['eac']}")
    print(f"验算: {'通过' if result['verify']['passed'] else '失败'} {'; '.join(result['verify']['notes'])}")
