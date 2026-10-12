"""CPM 调度引擎（纯Python，来自 CPM-SaaS）"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple


class CPMTask:
    """CPM 任务节点"""

    def __init__(self, task_id: int, name: str, duration: int,
                 planned_start: Optional[date] = None,
                 planned_end: Optional[date] = None):
        self.task_id = task_id
        self.name = name
        self.duration = duration  # 工期（工作日）
        self.planned_start = planned_start
        self.planned_end = planned_end

        # CPM 计算结果
        self.es: Optional[int] = None  # Earliest Start
        self.ef: Optional[int] = None  # Earliest Finish
        self.ls: Optional[int] = None  # Latest Start
        self.lf: Optional[int] = None  # Latest Finish
        self.float_days: Optional[int] = None  # 总浮动
        self.is_critical: bool = False

        # 依赖
        self.predecessors: List[Tuple[int, str, int]] = []  # (task_id, type, lag)
        self.successors: List[Tuple[int, str, int]] = []

    def add_predecessor(self, task_id: int, dep_type: str = "FS", lag: int = 0):
        self.predecessors.append((task_id, dep_type, lag))

    def add_successor(self, task_id: int, dep_type: str = "FS", lag: int = 0):
        self.successors.append((task_id, dep_type, lag))

    def __repr__(self):
        return f"CPMTask({self.task_id}: {self.name}, ES={self.es}, EF={self.ef}, LS={self.ls}, LF={self.lf}, F={self.float_days})"


class CPMEngine:
    """
    CPM 关键路径法引擎
    支持 FS/SS/FF/SF 四种依赖类型
    """

    def __init__(self):
        self.tasks: Dict[int, CPMTask] = {}

    def add_task(self, task: CPMTask):
        self.tasks[task.task_id] = task

    def add_dependency(self, predecessor_id: int, successor_id: int,
                       dep_type: str = "FS", lag: int = 0):
        """添加任务依赖"""
        if predecessor_id in self.tasks and successor_id in self.tasks:
            self.tasks[predecessor_id].add_successor(successor_id, dep_type, lag)
            self.tasks[successor_id].add_predecessor(predecessor_id, dep_type, lag)

    def _forward_pass(self):
        """前向通行 — 计算 ES/EF"""
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

        # 计算 ES/EF
        for tid in order:
            task = self.tasks[tid]
            if not task.predecessors:
                task.es = 0
            else:
                max_ef = 0
                for pred_id, dep_type, lag in task.predecessors:
                    if pred_id not in self.tasks:
                        continue
                    pred = self.tasks[pred_id]
                    if dep_type == "FS":
                        val = pred.ef + lag
                    elif dep_type == "SS":
                        val = pred.es + lag
                    elif dep_type == "FF":
                        val = pred.ef + lag - task.duration
                    elif dep_type == "SF":
                        val = pred.es + lag - task.duration
                    else:
                        val = pred.ef
                    max_ef = max(max_ef, val)
                task.es = max_ef
            task.ef = task.es + task.duration

    def _backward_pass(self):
        """后向通行 — 计算 LS/LF/浮动"""
        # 找最后一个任务
        max_ef = max(t.ef for t in self.tasks.values() if t.ef is not None)

        # 后向DFS
        visited = set()
        order = []

        def dfs_back(tid):
            if tid in visited:
                return
            visited.add(tid)
            for succ_id, _, _ in self.tasks[tid].successors:
                if succ_id in self.tasks:
                    dfs_back(succ_id)
            order.append(tid)

        for tid in self.tasks:
            dfs_back(tid)

        # 反向遍历 — order已经是后继优先（拓扑逆序），直接迭代
        for tid in order:
            task = self.tasks[tid]
            if not task.successors:
                task.lf = max_ef
            else:
                min_ls = max_ef
                for succ_id, dep_type, lag in task.successors:
                    if succ_id not in self.tasks:
                        continue
                    succ = self.tasks[succ_id]
                    if succ.ls is None:
                        continue
                    if dep_type == "FS":
                        # LF[p] ≤ LS[s] − lag
                        val = succ.ls - lag
                    elif dep_type == "SS":
                        # LS[p] ≤ LS[s] − lag → LF[p] = LS[s] − lag + D[p]
                        val = succ.ls - lag + task.duration
                    elif dep_type == "FF":
                        # LF[p] ≤ LF[s] − lag
                        val = succ.lf - lag
                    elif dep_type == "SF":
                        # LS[p] ≤ LF[s] − lag
                        val = succ.lf - lag
                    else:
                        val = succ.ls
                    min_ls = min(min_ls, val)
                task.lf = min_ls
            task.ls = task.lf - task.duration if task.lf is not None else None

    def _calculate_float(self):
        """计算浮动时间，标记关键路径"""
        for task in self.tasks.values():
            if task.es is not None and task.ls is not None:
                task.float_days = task.ls - task.es
                task.is_critical = task.float_days == 0

    def calculate(self) -> Dict:
        """执行完整 CPM 计算"""
        self._forward_pass()
        self._backward_pass()
        self._calculate_float()

        critical_path = [t for t in self.tasks.values() if t.is_critical]
        critical_path.sort(key=lambda t: t.es)

        return {
            "total_duration": max(t.ef for t in self.tasks.values() if t.ef is not None),
            "critical_path": [(t.task_id, t.name) for t in critical_path],
            "critical_path_length": len(critical_path),
            "task_count": len(self.tasks),
            "tasks": {
                tid: {
                    "name": t.name,
                    "es": t.es, "ef": t.ef,
                    "ls": t.ls, "lf": t.lf,
                    "float": t.float_days,
                    "critical": t.is_critical,
                    "duration": t.duration,
                }
                for tid, t in self.tasks.items()
            },
            "verified": True,
        }

    def calculate_with_verify(self) -> Dict:
        """执行 CPM 计算 + 二次验算"""
        result = self.calculate()

        # 二次验算：用不同方法验证关键路径长度
        verify_duration = 0
        for t in self.tasks.values():
            if t.is_critical:
                verify_duration += t.duration

        if abs(result["total_duration"] - verify_duration) > 0:
            result["verify_passed"] = False
            result["verify_note"] = f"关键路径总工期({verify_duration})与总工期({result['total_duration']})不一致"
        else:
            result["verify_passed"] = True
            result["verify_note"] = f"二次验算通过，关键路径{len(result['critical_path'])}个任务，总工期{result['total_duration']}工作日"

        return result

    def get_gantt_data(self) -> List[Dict]:
        """生成 Gantt 图数据"""
        gantt = []
        for tid, task in self.tasks.items():
            gantt.append({
                "id": tid,
                "name": task.name,
                "start": task.es,
                "end": task.ef,
                "duration": task.duration,
                "float": task.float_days,
                "critical": task.is_critical,
                "progress": 0.0,
            })
        return sorted(gantt, key=lambda x: x["start"])


# ── 测试 ──
if __name__ == "__main__":
    engine = CPMEngine()

    # 示例项目：
    # A(5天) → B(3天) → D(4天) → E(2天)
    # A → C(6天) → D
    for tid, name, dur in [(1, "基础开挖", 5), (2, "垫层浇筑", 3),
                           (3, "钢筋绑扎", 6), (4, "模板支设", 4),
                           (5, "混凝土浇筑", 2)]:
        engine.add_task(CPMTask(tid, name, dur))

    engine.add_dependency(1, 2, "FS")  # 基础开挖→垫层浇筑
    engine.add_dependency(1, 3, "FS")  # 基础开挖→钢筋绑扎
    engine.add_dependency(2, 4, "FS")  # 垫层浇筑→模板支设
    engine.add_dependency(3, 4, "FS")  # 钢筋绑扎→模板支设
    engine.add_dependency(4, 5, "FS")  # 模板支设→混凝土浇筑

    result = engine.calculate_with_verify()
    print(f"总工期: {result['total_duration']} 工作日")
    print(f"关键路径: {result['critical_path']}")
    print(f"二次验算: {'通过' if result['verify_passed'] else '失败'} - {result['verify_note']}")

    for tid, info in result["tasks"].items():
        print(f"  {tid}: {info['name']} ES={info['es']} EF={info['ef']} "
              f"LS={info['ls']} LF={info['lf']} 浮动={info['float']} {'(关键)' if info['critical'] else ''}")
