"""仪表盘视图 — 卡片式概览"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.database.connection import DatabaseManager


class StatCard(QFrame):
    """统计卡片组件"""

    def __init__(self, title: str, value: str, icon: str = "", color: str = "#64748B"):
        super().__init__()
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            #statCard {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
                border-left: 4px solid {color};
            }}
            #statCard:hover {{
                border-color: #CBD5E1;
                background-color: #F8FAFC;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(icon_label)

        value_label = QLabel(value)
        value_label.setStyleSheet(
            "font-family: 'Lexend', 'Microsoft YaHei', sans-serif;"
            "font-size: 28px; font-weight: 700; color: #1E293B;"
        )
        layout.addWidget(value_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 13px; color: #64748B; font-weight: 500;"
        )
        layout.addWidget(title_label)


class DashboardView(QWidget):
    """仪表盘 — 项目全局概览"""

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题区
        title = QLabel("BuildCycle 建造全周期管控平台")
        title.setProperty("heading", "true")
        layout.addWidget(title)

        subtitle = QLabel("项目全局概览 · 一键掌握四阶段管控状态")
        subtitle.setProperty("subheading", "true")
        layout.addWidget(subtitle)

        # 统计卡片
        card_grid = QGridLayout()
        card_grid.setSpacing(16)

        self.cards = {
            "requirement": StatCard("需求与策划", "--", "📋", "#64748B"),
            "bidding": StatCard("招投标前期", "--", "📑", "#EA580C"),
            "construction": StatCard("施工实施", "--", "🏗️", "#16A34A"),
            "settlement": StatCard("竣工结算与维保", "--", "✅", "#2563EB"),
        }

        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for (key, card), (r, c) in zip(self.cards.items(), positions):
            card_grid.addWidget(card, r, c)

        layout.addLayout(card_grid)

        # 最近更新标题
        recent_header = QLabel("最近活动")
        recent_header.setProperty("heading", "true")
        layout.addWidget(recent_header)

        # 最近更新表格
        self.recent_table = QTableWidget(0, 4)
        self.recent_table.setHorizontalHeaderLabels(["模块", "项目", "内容", "更新时间"])
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.verticalHeader().setVisible(False)
        layout.addWidget(self.recent_table)

    def _load_data(self):
        """加载统计数据"""
        session = self.db.get_session()
        try:
            from app.database.models import (
                ProjectRequirement, BidDueDiligence, Contract,
                ProgressPlan, SafetyCheck, ChangeOrder,
                CompletionIssue, Settlement, WarrantyWorkOrder
            )

            req_count = session.query(ProjectRequirement).count()
            confirmed = session.query(ProjectRequirement).filter(
                ProjectRequirement.status == "confirmed"
            ).count()

            bid_count = session.query(BidDueDiligence).count()
            contract_count = session.query(Contract).filter(
                Contract.status == "active"
            ).count()

            progress_active = session.query(ProgressPlan).filter(
                ProgressPlan.status == "in_progress"
            ).count()
            change_pending = session.query(ChangeOrder).filter(
                ChangeOrder.status == "pending"
            ).count()

            settle_pending = session.query(Settlement).filter(
                Settlement.status == "pending"
            ).count()
            warranty_active = session.query(WarrantyWorkOrder).filter(
                WarrantyWorkOrder.status == "pending"
            ).count()

            self.cards["requirement"].findChildren(QLabel)[1].setText(
                f"{confirmed} / {req_count}" if req_count else "0"
            )
            self.cards["bidding"].findChildren(QLabel)[1].setText(
                f"{bid_count} 个尽调 · {contract_count} 份合同"
            )
            self.cards["construction"].findChildren(QLabel)[1].setText(
                f"{progress_active} 进行中 · {change_pending} 待审签证"
            )
            self.cards["settlement"].findChildren(QLabel)[1].setText(
                f"{settle_pending} 待结算 · {warranty_active} 待维修"
            )

            # 最近活动
            all_records = []
            for r in session.query(ProjectRequirement).order_by(ProjectRequirement.updated_at.desc()).limit(5):
                all_records.append(("需求与策划", r.project_name, "更新需求", r.updated_at))
            for r in session.query(ChangeOrder).order_by(ChangeOrder.created_at.desc()).limit(5):
                all_records.append(("施工实施", r.project_name, f"变更签证: {(r.change_desc or '')[:20]}", r.created_at))
            for r in session.query(Settlement).order_by(Settlement.created_at.desc()).limit(5):
                all_records.append(("竣工结算", r.project_name, "结算记录", r.created_at))

            all_records.sort(key=lambda x: x[3] or "", reverse=True)
            self.recent_table.setRowCount(min(len(all_records), 10))
            for i, (mod, proj, content, dt) in enumerate(all_records[:10]):
                self.recent_table.setItem(i, 0, QTableWidgetItem(mod))
                self.recent_table.setItem(i, 1, QTableWidgetItem(proj or ""))
                self.recent_table.setItem(i, 2, QTableWidgetItem(content))
                self.recent_table.setItem(i, 3, QTableWidgetItem(
                    str(dt.strftime("%Y-%m-%d %H:%M")) if dt else ""
                ))
        finally:
            session.close()
