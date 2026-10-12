"""资源平衡引擎（启发式，修复版）"""

from collections import defaultdict
from typing import List, Dict


class ResourceLevelingEngine:
    """资源平衡引擎"""

    def __init__(self):
        self.resources: Dict[str, float] = {}
        self.tasks: List[Dict] = []

    def add_resource(self, name: str, daily_capacity: float):
        self.resources[name] = daily_capacity

    def add_task(self, task_id: int, name: str, duration: int,
                 es: int, ef: int, ls: int, lf: int,
                 is_critical: bool, resource: str = "",
                 resource_amount: float = 1.0):
        self.tasks.append({
            "id": task_id, "name": name, "duration": duration,
            "es": es, "ef": ef, "ls": ls, "lf": lf,
            "is_critical": is_critical, "resource": resource,
            "resource_amount": resource_amount,
            "start": es,
        })

    def _get_load(self, tasks: List[Dict], exclude_task_id: int = None) -> Dict[str, Dict[int, float]]:
        load = {r: defaultdict(float) for r in self.resources}
        for t in tasks:
            if exclude_task_id is not None and t["id"] == exclude_task_id:
                continue
            if t["resource"] and t["resource"] in load:
                for d in range(t["duration"]):
                    load[t["resource"]][t["start"] + d] += t["resource_amount"]
        return load

    def level(self) -> Dict:
        tasks = [dict(t) for t in self.tasks]
        moves = []

        for iteration in range(10):
            load = self._get_load(tasks)

            overloaded_days = set()
            for rname, cap in self.resources.items():
                for day, l in load[rname].items():
                    if l > cap:
                        overloaded_days.add(day)

            if not overloaded_days:
                return {"moves": moves, "moves_count": len(moves),
                        "iterations": iteration + 1, "balanced": True, "tasks": tasks}

            candidates = [t for t in tasks if not t["is_critical"]
                         and t["resource"] in self.resources
                         and any(t["start"] + d in overloaded_days for d in range(t["duration"]))]
            candidates.sort(key=lambda t: t["ls"] - t["es"])

            moved = False
            for t in candidates:
                load_wo = self._get_load(tasks, exclude_task_id=t["id"])
                max_shift = t["lf"] - t["es"]

                for shift in range(1, max_shift + 1):
                    new_start = t["es"] + shift
                    ok = True
                    for d in range(t["duration"]):
                        day = new_start + d
                        if (load_wo[t["resource"]].get(day, 0) +
                            t["resource_amount"]) > self.resources[t["resource"]]:
                            ok = False
                            break
                    if ok:
                        old = t["start"]
                        t["start"] = new_start
                        moves.append({
                            "task_id": t["id"], "task_name": t["name"],
                            "from": old, "to": new_start,
                            "shift_days": shift,
                        })
                        moved = True
                        break

            if not moved:
                break

        return {"moves": moves, "moves_count": len(moves),
                "iterations": iteration + 1, "balanced": False, "tasks": tasks}


if __name__ == "__main__":
    eng = ResourceLevelingEngine()
    eng.add_resource("工人", 4)
    eng.add_task(1, "基础开挖", 5, 0, 5, 0, 5, True, "工人", 2)
    eng.add_task(2, "垫层浇筑", 3, 5, 8, 8, 11, False, "工人", 3)
    eng.add_task(3, "钢筋绑扎", 6, 5, 11, 5, 11, True, "工人", 2)
    eng.add_task(4, "模板支设", 4, 11, 15, 11, 15, True, "工人", 2)
    eng.add_task(5, "混凝土浇筑", 2, 15, 17, 15, 17, True, "工人", 3)

    r = eng.level()
    print(f"平衡完成: {r['balanced']}, 移动: {r['moves_count']}次")
    for m in r["moves"]:
        print(f"  ➡ 移动: {m['task_name']} 第{m['from']}天→第{m['to']}天")
    for t in r["tasks"]:
        print(f"  {t['name']}: 开始第{t['start']}天, 浮动{t['ls']-t['es']}天, {'关键' if t['is_critical'] else ''}")
