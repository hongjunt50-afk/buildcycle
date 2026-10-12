"""施工实施视图 — 进度/质量/安全/变更/资料"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QTabWidget
)

from app.database.connection import DatabaseManager


class ConstructionView(QWidget):
    """施工实施模块视图"""

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题区
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("施工实施管理")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("进度计划、质量三检、安全管理、变更签证、施工资料同步")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        layout.addLayout(header)

        self.tabs = QTabWidget()

        # 进度计划
        self.progress_table = QTableWidget(0, 7)
        self.progress_table.setHorizontalHeaderLabels(["ID", "任务", "计划开始", "计划结束", "进度%", "滞后天数", "状态"])
        self.progress_table.horizontalHeader().setStretchLastSection(True)
        self.progress_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.progress_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.progress_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.progress_table.setAlternatingRowColors(True)
        self.progress_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.progress_table, "📅 进度计划")

        # 质量检查
        self.quality_table = QTableWidget(0, 6)
        self.quality_table.setHorizontalHeaderLabels(["ID", "检查类型", "检查项", "结果", "检查人", "日期"])
        self.quality_table.horizontalHeader().setStretchLastSection(True)
        self.quality_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.quality_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.quality_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.quality_table.setAlternatingRowColors(True)
        self.quality_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.quality_table, "🔍 质量三检")

        # 安全检查
        self.safety_table = QTableWidget(0, 6)
        self.safety_table.setHorizontalHeaderLabels(["ID", "隐患项", "等级", "整改要求", "状态", "创建时间"])
        self.safety_table.horizontalHeader().setStretchLastSection(True)
        self.safety_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.safety_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.safety_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.safety_table.setAlternatingRowColors(True)
        self.safety_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.safety_table, "⚠️ 安全管理")

        # 变更签证
        self.change_table = QTableWidget(0, 6)
        self.change_table.setHorizontalHeaderLabels(["ID", "变更描述", "金额(万元)", "申请人", "状态", "创建时间"])
        self.change_table.horizontalHeader().setStretchLastSection(True)
        self.change_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.change_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.change_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.change_table.setAlternatingRowColors(True)
        self.change_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.change_table, "📝 变更签证")

        # 施工资料
        self.doc_table = QTableWidget(0, 5)
        self.doc_table.setHorizontalHeaderLabels(["ID", "资料类型", "关联施工日期", "同步录入", "创建时间"])
        self.doc_table.horizontalHeader().setStretchLastSection(True)
        self.doc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.doc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.doc_table.setAlternatingRowColors(True)
        self.doc_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.doc_table, "📄 施工资料")

        layout.addWidget(self.tabs)
        self._load_data()

    def _load_data(self):
        session = self.db.get_session()
        try:
            from app.database.models import ProgressPlan, QualityCheck, SafetyCheck, ChangeOrder, ConstructionDoc

            for r in session.query(ProgressPlan).order_by(ProgressPlan.id.desc()).all():
                row = self.progress_table.rowCount()
                self.progress_table.insertRow(row)
                self.progress_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.progress_table.setItem(row, 1, QTableWidgetItem(r.task_name or ""))
                self.progress_table.setItem(row, 2, QTableWidgetItem(str(r.planned_start.date()) if r.planned_start else ""))
                self.progress_table.setItem(row, 3, QTableWidgetItem(str(r.planned_end.date()) if r.planned_end else ""))
                self.progress_table.setItem(row, 4, QTableWidgetItem(str(r.progress_pct)))
                self.progress_table.setItem(row, 5, QTableWidgetItem(str(r.delay_days)))
                self.progress_table.setItem(row, 6, QTableWidgetItem(r.status))

            for r in session.query(QualityCheck).order_by(QualityCheck.id.desc()).all():
                row = self.quality_table.rowCount()
                self.quality_table.insertRow(row)
                self.quality_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.quality_table.setItem(row, 1, QTableWidgetItem(r.check_type or ""))
                self.quality_table.setItem(row, 2, QTableWidgetItem(r.check_item or ""))
                self.quality_table.setItem(row, 3, QTableWidgetItem(r.check_result or ""))
                self.quality_table.setItem(row, 4, QTableWidgetItem(r.inspector or ""))
                self.quality_table.setItem(row, 5, QTableWidgetItem(str(r.check_date.date()) if r.check_date else ""))

            for r in session.query(SafetyCheck).order_by(SafetyCheck.id.desc()).all():
                row = self.safety_table.rowCount()
                self.safety_table.insertRow(row)
                self.safety_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.safety_table.setItem(row, 1, QTableWidgetItem(r.hazard_item or ""))
                self.safety_table.setItem(row, 2, QTableWidgetItem(r.hazard_level or ""))
                self.safety_table.setItem(row, 3, QTableWidgetItem((r.rectification or "")[:40]))
                self.safety_table.setItem(row, 4, QTableWidgetItem(r.status))
                self.safety_table.setItem(row, 5, QTableWidgetItem(str(r.created_at.date()) if r.created_at else ""))

            for r in session.query(ChangeOrder).order_by(ChangeOrder.id.desc()).all():
                row = self.change_table.rowCount()
                self.change_table.insertRow(row)
                self.change_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.change_table.setItem(row, 1, QTableWidgetItem((r.change_desc or "")[:50]))
                self.change_table.setItem(row, 2, QTableWidgetItem(str(r.amount_change or 0)))
                self.change_table.setItem(row, 3, QTableWidgetItem(r.applicant or ""))
                self.change_table.setItem(row, 4, QTableWidgetItem(r.status))
                self.change_table.setItem(row, 5, QTableWidgetItem(str(r.created_at.date()) if r.created_at else ""))

            for r in session.query(ConstructionDoc).order_by(ConstructionDoc.id.desc()).all():
                row = self.doc_table.rowCount()
                self.doc_table.insertRow(row)
                self.doc_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.doc_table.setItem(row, 1, QTableWidgetItem(r.doc_type or ""))
                self.doc_table.setItem(row, 2, QTableWidgetItem(str(r.related_date.date()) if r.related_date else ""))
                self.doc_table.setItem(row, 3, QTableWidgetItem("是" if r.is_synced else "否"))
                self.doc_table.setItem(row, 4, QTableWidgetItem(str(r.created_at.date()) if r.created_at else ""))
        finally:
            session.close()
