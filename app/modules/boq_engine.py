"""新建被测项目引擎：app/modules/boq_engine.py（M9 实战轮抽取）。

只做纯计算与数据联动，不依赖 Qt：
- item_total(q, p): 条目合价 = round(量×价, 2)
- recompute_section(session, section_id): 章节小计 = Σ条目合价（单一实现，
  供 UI 增/删/改共用——修复 boq_view._on_delete_item 删后小计不回落）
"""
from __future__ import annotations


def item_total(quantity: float, unit_price: float) -> float:
    """条目合价：量×价，保留 2 位（清单计价惯例）。"""
    return round(float(quantity) * float(unit_price), 2)


def recompute_section(session, section_id: int) -> float:
    """重算章节小计 = 章节内全部条目合价之和。

    单一实现：任何条目增/删/改后调用一次即可，杜绝口径分叉。
    返回新小计（不 commit，由调用方统一提交）。
    """
    from app.database.models import BoqItem, BoqSection

    sec = session.query(BoqSection).get(section_id)
    if sec is None:
        return 0.0
    total = sum(i.total_price or 0 for i in
                session.query(BoqItem).filter(BoqItem.section_id == section_id).all())
    sec.subtotal = round(total, 2)
    return sec.subtotal
