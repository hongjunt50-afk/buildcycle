"""蒙特卡洛风险分析引擎（来自 CPM-SaaS）"""

import random
import math
from typing import List, Dict, Optional, Tuple
from collections import Counter


class PERTTask:
    """PERT 三点估算任务"""

    def __init__(self, task_id: int, name: str,
                 optimistic: int, most_likely: int, pessimistic: int):
        self.task_id = task_id
        self.name = name
        self.optimistic = optimistic      # 乐观工期
        self.most_likely = most_likely    # 最可能工期
        self.pessimistic = pessimistic    # 悲观工期

        # 计算期望工期和标准差
        self.expected = (optimistic + 4 * most_likely + pessimistic) / 6
        self.std_dev = (pessimistic - optimistic) / 6
        self.variance = self.std_dev ** 2

        self.predecessors: List[Tuple[int, str, int]] = []

    def add_predecessor(self, task_id: int, dep_type: str = "FS", lag: int = 0):
        self.predecessors.append((task_id, dep_type, lag))

    def sample_duration(self) -> int:
        """使用三角分布采样工期"""
        # 三角分布采样
        u = random.random()
        fc = (self.most_likely - self.optimistic) / (self.pessimistic - self.optimistic)
        if u <= fc:
            return int(self.optimistic + math.sqrt(u * (self.pessimistic - self.optimistic) * (self.most_likely - self.optimistic)))
        else:
            return int(self.pessimistic - math.sqrt((1 - u) * (self.pessimistic - self.optimistic) * (self.pessimistic - self.most_likely)))


class MonteCarloEngine:
    """
    蒙特卡洛 PERT 风险分析
    - 使用 PERT 三点估算
    - 执行蒙特卡洛模拟
    - 生成完成 S 曲线 + 关键性指数
    """

    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.tasks: Dict[int, PERTTask] = {}

    def add_task(self, task: PERTTask):
        self.tasks[task.task_id] = task

    def add_dependency(self, predecessor_id: int, successor_id: int,
                       dep_type: str = "FS", lag: int = 0):
        if predecessor_id in self.tasks and successor_id in self.tasks:
            self.tasks[successor_id].add_predecessor(predecessor_id, dep_type, lag)

    def _run_single_simulation(self) -> Tuple[int, Dict[int, int]]:
        """单次模拟，返回总工期和每个任务的完成时间"""
        completion_times = {}
        max_duration = 0

        # 拓扑排序
        visited = set()
        order = []

        def dfs(tid):
            if tid in visited:
                return
            visited.add(tid)
            for pred_id, _, _ in self.tasks[tid].predecessors:
                if pred_id in self.tasks:
                    dfs(pred_id)
            order.append(tid)

        for tid in self.tasks:
            dfs(tid)

        for tid in order:
            task = self.tasks[tid]
            duration = task.sample_duration()

            if not task.predecessors:
                start = 0
            else:
                start = 0
                for pred_id, dep_type, lag in task.predecessors:
                    if pred_id in completion_times:
                        pred_end = completion_times[pred_id]
                        if dep_type == "FS":
                            start = max(start, pred_end + lag)
                        elif dep_type == "SS":
                            start = max(start, pred_end + lag - duration)
                        elif dep_type == "FF":
                            start = max(start, pred_end + lag - duration)
                        elif dep_type == "SF":
                            start = max(start, pred_end + lag)

            end = start + duration
            completion_times[tid] = end
            max_duration = max(max_duration, end)

        return max_duration, completion_times

    def run(self) -> Dict:
        """执行蒙特卡洛模拟"""
        durations = []
        criticality = Counter()

        for i in range(self.iterations):
            total_dur, comp_times = self._run_single_simulation()
            durations.append(total_dur)

            # 记录关键路径上的任务（最晚完成的任务）
            max_time = max(comp_times.values())
            for tid, t in comp_times.items():
                if t == max_time:
                    criticality[tid] += 1

        # 统计分析
        durations.sort()
        n = len(durations)

        mean = sum(durations) / n
        variance = sum((d - mean) ** 2 for d in durations) / n
        std_dev = math.sqrt(variance)

        # 百分位数
        p10 = durations[int(n * 0.1)]
        p25 = durations[int(n * 0.25)]
        p50 = durations[int(n * 0.5)]
        p75 = durations[int(n * 0.75)]
        p90 = durations[int(n * 0.9)]

        # S 曲线数据
        s_curve = []
        for day in range(int(durations[0]), int(durations[-1]) + 1):
            count = sum(1 for d in durations if d <= day)
            prob = count / n * 100
            s_curve.append({"day": day, "probability": round(prob, 1)})

        # 关键性指数
        criticality_index = {
            tid: round(count / n * 100, 1)
            for tid, count in criticality.most_common()
        }

        return {
            "iterations": self.iterations,
            "statistics": {
                "mean": round(mean, 1),
                "std_dev": round(std_dev, 1),
                "min": durations[0],
                "max": durations[-1],
            },
            "percentiles": {
                "p10": p10,
                "p25": p25,
                "p50": p50,
                "p75": p75,
                "p90": p90,
            },
            "s_curve": s_curve,
            "criticality_index": criticality_index,
            "durations": durations[:100],  # 只返回前100个样本
        }


if __name__ == "__main__":
    mc = MonteCarloEngine(iterations=1000)

    # 示例项目
    mc.add_task(PERTTask(1, "基础开挖", 3, 5, 8))
    mc.add_task(PERTTask(2, "垫层浇筑", 2, 3, 5))
    mc.add_task(PERTTask(3, "钢筋绑扎", 4, 6, 10))
    mc.add_task(PERTTask(4, "模板支设", 3, 4, 6))
    mc.add_task(PERTTask(5, "混凝土浇筑", 1, 2, 4))

    mc.add_dependency(1, 2, "FS")
    mc.add_dependency(1, 3, "FS")
    mc.add_dependency(2, 4, "FS")
    mc.add_dependency(3, 4, "FS")
    mc.add_dependency(4, 5, "FS")

    result = mc.run()

    print(f"蒙特卡洛模拟 ({result['iterations']}次)")
    print(f"\n统计:")
    print(f"  期望工期: {result['statistics']['mean']}天")
    print(f"  标准差: {result['statistics']['std_dev']}天")
    print(f"  最短: {result['statistics']['min']}天")
    print(f"  最长: {result['statistics']['max']}天")
    print(f"\n百分位数:")
    print(f"  P10: {result['percentiles']['p10']}天")
    print(f"  P25: {result['percentiles']['p25']}天")
    print(f"  P50: {result['percentiles']['p50']}天")
    print(f"  P75: {result['percentiles']['p75']}天")
    print(f"  P90: {result['percentiles']['p90']}天")
    print(f"\n关键性指数 (Top 3):")
    for tid, idx in sorted(result['criticality_index'].items(), key=lambda x: -x[1])[:3]:
        print(f"  任务{tid}: {idx}%")

    print(f"\nS曲线样本 (前10天):")
    for point in result['s_curve'][:10]:
        print(f"  第{point['day']}天: 完成概率 {point['probability']}%")
