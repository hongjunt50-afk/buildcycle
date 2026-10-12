"""竣工结算与维保视图"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QTabWidget
)

from app.database.connection import DatabaseManager


class SettlementView(QWidget):
    """竣工结算与维保模块视图"""

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
        title = QLabel("竣工结算与维保管理")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("验收整改、结算对账、质保报修、质保金跟踪")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        layout.addLayout(header)

        self.tabs = QTabWidget()

        # 验收整改
        self.issue_table = QTableWidget(0, 5)
        self.issue_table.setHorizontalHeaderLabels(["ID", "问题描述", "责任人", "状态", "创建时间"])
        self.issue_table.horizontalHeader().setStretchLastSection(True)
        self.issue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.issue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.issue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.issue_table.setAlternatingRowColors(True)
        self.issue_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.issue_table, "🔧 验收整改")

        # 结算对账
        self.settlement_table = QTableWidget(0, 6)
        self.settlement_table.setHorizontalHeaderLabels(["ID", "项目", "合同金额", "变更金额", "结算金额", "状态"])
        self.settlement_table.horizontalHeader().setStretchLastSection(True)
        self.settlement_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.settlement_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.settlement_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.settlement_table.setAlternatingRowColors(True)
        self.settlement_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.settlement_table, "💰 结算对账")

        # 质保报修
        self.warranty_table = QTableWidget(0, 6)
        self.warranty_table.setHorizontalHeaderLabels(["ID", "项目", "报修人", "问题描述", "状态", "创建时间"])
        self.warranty_table.horizontalHeader().setStretchLastSection(True)
        self.warranty_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.warranty_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.warranty_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.warranty_table.setAlternatingRowColors(True)
        self.warranty_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.warranty_table, "🔧 质保报修")

        # 质保金跟踪
        self.deposit_table = QTableWidget(0, 5)
        self.deposit_table.setHorizontalHeaderLabels(["ID", "项目", "金额(万元)", "到期日", "状态"])
        self.deposit_table.horizontalHeader().setStretchLastSection(True)
        self.deposit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.deposit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.deposit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.deposit_table.setAlternatingRowColors(True)
        self.deposit_table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.deposit_table, "🏦 质保金跟踪")

        layout.addWidget(self.tabs)
        self._load_data()

    def _load_data(self):
        session = self.db.get_session()
        try:
            from app.database.models import CompletionIssue, Settlement, WarrantyWorkOrder, WarrantyDeposit

            for r in session.query(CompletionIssue).order_by(CompletionIssue.id.desc()).all():
                row = self.issue_table.rowCount()
                self.issue_table.insertRow(row)
                self.issue_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.issue_table.setItem(row, 1, QTableWidgetItem((r.issue_desc or "")[:50]))
                self.issue_table.setItem(row, 2, QTableWidgetItem(r.responsible_person or ""))
                self.issue_table.setItem(row, 3, QTableWidgetItem(r.status))
                self.issue_table.setItem(row, 4, QTableWidgetItem(str(r.created_at.date()) if r.created_at else ""))

            for r in session.query(Settlement).order_by(Settlement.id.desc()).all():
                row = self.settlement_table.rowCount()
                self.settlement_table.insertRow(row)
                self.settlement_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.settlement_table.setItem(row, 1, QTableWidgetItem(r.project_name or ""))
                self.settlement_table.setItem(row, 2, QTableWidgetItem(str(r.contract_amount or 0)))
                self.settlement_table.setItem(row, 3, QTableWidgetItem(str(r.change_amount or 0)))
                self.settlement_table.setItem(row, 4, QTableWidgetItem(str(r.settlement_amount or "")))
                self.settlement_table.setItem(row, 5, QTableWidgetItem(r.status))

            for r in session.query(WarrantyWorkOrder).order_by(WarrantyWorkOrder.id.desc()).all():
                row = self.warranty_table.rowCount()
                self.warranty_table.insertRow(row)
                self.warranty_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.warranty_table.setItem(row, 1, QTableWidgetItem(r.project_name or ""))
                self.warranty_table.setItem(row, 2, QTableWidgetItem(r.reporter or ""))
                self.warranty_table.setItem(row, 3, QTableWidgetItem((r.issue_desc or "")[:40]))
                self.warranty_table.setItem(row, 4, QTableWidgetItem(r.status))
                self.warranty_table.setItem(row, 5, QTableWidgetItem(str(r.created_at.date()) if r.created_at else ""))

            for r in session.query(WarrantyDeposit).order_by(WarrantyDeposit.id.desc()).all():
                row = self.deposit_table.rowCount()
                self.deposit_table.insertRow(row)
                self.deposit_table.setItem(row, 0, QTableWidgetItem(str(r.id)))
                self.deposit_table.setItem(row, 1, QTableWidgetItem(r.project_name or ""))
                self.deposit_table.setItem(row, 2, QTableWidgetItem(str(r.deposit_amount or 0)))
                self.deposit_table.setItem(row, 3, QTableWidgetItem(str(r.expiry_date.date()) if r.expiry_date else ""))
                self.deposit_table.setItem(row, 4, QTableWidgetItem(r.status))
        finally:
            session.close()
