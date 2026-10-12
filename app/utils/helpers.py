"""工具函数"""

import json
from datetime import datetime
from pathlib import Path


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def now_str() -> str:
    """当前时间字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def date_str() -> str:
    """当前日期字符串"""
    return datetime.now().strftime("%Y-%m-%d")


def load_json(path: str) -> dict:
    """加载JSON文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    """保存JSON文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
