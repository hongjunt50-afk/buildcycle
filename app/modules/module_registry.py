"""可插拔模块架构 — 类似 Massing 的 module.json 自动注册"""

import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Callable


class ModuleDescriptor:
    """模块描述符 — 每个模块一个JSON"""

    def __init__(self, module_dir: Path):
        self.module_dir = module_dir
        self.descriptor_path = module_dir / "module.json"
        self._data = {}
        if self.descriptor_path.exists():
            with open(self.descriptor_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    @property
    def name(self) -> str:
        return self._data.get("name", self.module_dir.name)

    @property
    def version(self) -> str:
        return self._data.get("version", "0.1.0")

    @property
    def description(self) -> str:
        return self._data.get("description", "")

    @property
    def tables(self) -> List[Dict]:
        """模块需要的数据库表定义"""
        return self._data.get("tables", [])

    @property
    def menu_item(self) -> Optional[Dict]:
        """菜单项定义"""
        return self._data.get("menu", None)

    @property
    def dependencies(self) -> List[str]:
        return self._data.get("dependencies", [])

    @property
    def enabled(self) -> bool:
        return self._data.get("enabled", True)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tables": len(self.tables),
            "has_menu": self.menu_item is not None,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
        }


class ModuleRegistry:
    """模块注册中心"""

    def __init__(self, modules_dir: str = None):
        from app.utils.config import settings
        self.modules_dir = Path(modules_dir or settings.ROOT_DIR / "app" / "modules")
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self._modules: Dict[str, ModuleDescriptor] = {}
        self._scan()

    def _scan(self):
        """扫描模块目录"""
        self._modules.clear()
        for child in self.modules_dir.iterdir():
            if child.is_dir() and (child / "module.json").exists():
                desc = ModuleDescriptor(child)
                if desc.enabled:
                    self._modules[desc.name] = desc

    def register_module(self, module_dir: str, descriptor: dict):
        """注册一个新模块"""
        path = Path(module_dir)
        path.mkdir(parents=True, exist_ok=True)
        desc_path = path / "module.json"
        with open(desc_path, "w", encoding="utf-8") as f:
            json.dump(descriptor, f, ensure_ascii=False, indent=2)
        self._scan()

    def list_modules(self) -> List[Dict]:
        """列出所有已注册模块"""
        return [m.to_dict() for m in self._modules.values()]

    def get_module(self, name: str) -> Optional[ModuleDescriptor]:
        return self._modules.get(name)

    def get_all_tables(self) -> List[Dict]:
        """收集所有模块的表定义"""
        all_tables = []
        for m in self._modules.values():
            all_tables.extend(m.tables)
        return all_tables


# 预设模块模板

CHANGE_ORDER_MODULE = {
    "name": "变更签证审批",
    "version": "1.0.0",
    "description": "变更签证发起→审批→确认→归档全流程管理",
    "enabled": True,
    "dependencies": [],
    "menu": {
        "tab": "施工实施",
        "label": "变更签证",
    },
    "tables": [
        {
            "name": "change_order",
            "comment": "变更签证记录",
            "columns": [
                {"name": "id", "type": "integer", "pk": True},
                {"name": "project_name", "type": "string", "length": 200},
                {"name": "change_desc", "type": "text"},
                {"name": "amount_change", "type": "float"},
                {"name": "status", "type": "string", "default": "pending"},
            ]
        }
    ]
}

BOQ_MODULE = {
    "name": "工程量清单",
    "version": "1.0.0",
    "description": "BOQ工程量清单管理，章节+条目+自动计算+导出",
    "enabled": True,
    "dependencies": [],
    "menu": {
        "tab": "招投标前期",
        "label": "工程量清单",
    },
}

CPM_MODULE = {
    "name": "进度计划",
    "version": "1.0.0",
    "description": "CPM关键路径法调度引擎，Gantt图，资源平衡",
    "enabled": True,
    "dependencies": [],
    "menu": {
        "tab": "施工实施",
        "label": "进度计划",
    },
}


# 全局实例
registry = ModuleRegistry()


if __name__ == "__main__":
    print(f"模块目录: {registry.modules_dir}")
    print(f"已注册模块: {len(registry.list_modules())}")
    for m in registry.list_modules():
        print(f"  - {m['name']} v{m['version']}: {m['description'][:40]}...")

    # 注册示例模块
    test_dir = registry.modules_dir / "test_change_order"
    registry.register_module(str(test_dir), CHANGE_ORDER_MODULE)
    print(f"\n注册后: {len(registry.list_modules())} 个模块")
    for m in registry.list_modules():
        print(f"  - {m['name']}: {'✅ 活跃' if m['enabled'] else '❌ 停用'}")
