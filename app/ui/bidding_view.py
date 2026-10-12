"""招投标前期视图 — 带子标签页"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QTabWidget, QFrame, QDialog,
    QFormLayout, QTextEdit, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt

from app.database.connection import DatabaseManager


class DueDiligenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增尽调记录")
        self.resize(500, 400)
        layout = QFormLayout(self)
        layout.setSpacing(12)
        self.project_name = QLineEdit()
        self.owner_name = QLineEdit()
        self.fund_source = QTextEdit()
        self.fund_source.setMaximumHeight(80)
        self.risk_notes = QTextEdit()
        self.risk_notes.setMaximumHeight(80)
        layout.addRow("项目名称：", self.project_name)
        layout.addRow("业主名称：", self.owner_name)
        layout.addRow("资金来源：", self.fund_source)
        layout.addRow("风险备注：", self.risk_notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "project_name": self.project_name.text(),
            "owner_name": self.owner_name.text(),
            "fund_source": self.fund_source.toPlainText(),
            "risk_notes": self.risk_notes.toPlainText(),
        }


class BiddingView(QWidget):
    """招投标前期模块视图"""

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
        title = QLabel("招投标前期管理")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("项目尽调、合同管理、标书与报价")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        layout.addLayout(header)

        # 子标签页
        self.tabs = QTabWidget()

        # 尽调台账
        diligence_widget = QWidget()
        dl = QVBoxLayout(diligence_widget)
        dl.setContentsMargins(0, 8, 0, 0)

        self.diligence_table = QTableWidget(0, 5)
        self.diligence_table.setHorizontalHeaderLabels(["ID", "项目名称", "业主", "资金来源", "风险备注"])
        self.diligence_table.horizontalHeader().setStretchLastSection(True)
        self.diligence_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.diligence_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.diligence_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.diligence_table.setAlternatingRowColors(True)
        self.diligence_table.verticalHeader().setVisible(False)
        dl.addWidget(self.diligence_table)

        btn_diligence = QPushButton("＋ 新增尽调")
        btn_diligence.clicked.connect(self._add_diligence)
        dl.addWidget(btn_diligence)

        btn_del_diligence = QPushButton("🗑️ 删除尽调")
        btn_del_diligence.clicked.connect(self._del_diligence)
        dl.addWidget(btn_del_diligence)

        self.tabs.addTab(diligence_widget, "项目尽调台账")

        # 合同管理
        contract_widget = QWidget()
        cl = QVBoxLayout(contract_widget)
        cl.setContentsMargins(0, 8, 0, 0)

        self.contract_table = QTableWidget(0, 6)
        self.contract_table.setHorizontalHeaderLabels(["ID", "项目名称", "合同编号", "合同类型", "风险标签", "状态"])
        self.contract_table.horizontalHeader().setStretchLastSection(True)
        self.contract_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.contract_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.contract_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.contract_table.setAlternatingRowColors(True)
        self.contract_table.verticalHeader().setVisible(False)
        cl.addWidget(self.contract_table)

        btn_del_contract = QPushButton("🗑️ 删除合同")
        btn_del_contract.clicked.connect(self._del_contract)
        cl.addWidget(btn_del_contract)

        self.tabs.addTab(contract_widget, "合同管理")

        layout.addWidget(self.tabs)

        self._load_data()

    def _add_diligence(self):
        dialog = DueDiligenceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            session = self.db.get_session()
            try:
                from app.database.models import BidDueDiligence
                record = BidDueDiligence(**data)
                session.add(record)
                session.commit()
                self._load_data()
            finally:
                session.close()

    def _del_diligence(self):
        """删除尽调记录"""
        row = self.diligence_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的尽调记录")
            return
        record_id = int(self.diligence_table.item(row, 0).text())
        reply = QMessageBox.question(self, "确认删除", "确定要删除此尽调记录？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                from app.database.models import BidDueDiligence
                record = session.query(BidDueDiligence).get(record_id)
                if record:
                    session.delete(record)
                    session.commit()
                    self._load_data()
            finally:
                session.close()

    def _del_contract(self):
        """删除合同"""
        row = self.contract_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的合同")
            return
        record_id = int(self.contract_table.item(row, 0).text())
        reply = QMessageBox.question(self, "确认删除", "确定要删除此合同？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                from app.database.models import Contract
                record = session.query(Contract).get(record_id)
                if record:
                    session.delete(record)
                    session.commit()
                    self._load_data()
            finally:
                session.close()

    def _load_data(self):
        session = self.db.get_session()
        try:
            from app.database.models import BidDueDiligence, Contract

            dilis = session.query(BidDueDiligence).order_by(BidDueDiligence.id.desc()).all()
            self.diligence_table.setRowCount(len(dilis))
            for i, r in enumerate(dilis):
                self.diligence_table.setItem(i, 0, QTableWidgetItem(str(r.id)))
                self.diligence_table.setItem(i, 1, QTableWidgetItem(r.project_name or ""))
                self.diligence_table.setItem(i, 2, QTableWidgetItem(r.owner_name or ""))
                self.diligence_table.setItem(i, 3, QTableWidgetItem((r.fund_source or "")[:40]))
                self.diligence_table.setItem(i, 4, QTableWidgetItem((r.risk_notes or "")[:40]))

            contracts = session.query(Contract).order_by(Contract.id.desc()).all()
            self.contract_table.setRowCount(len(contracts))
            for i, r in enumerate(contracts):
                self.contract_table.setItem(i, 0, QTableWidgetItem(str(r.id)))
                self.contract_table.setItem(i, 1, QTableWidgetItem(r.project_name or ""))
                self.contract_table.setItem(i, 2, QTableWidgetItem(r.contract_no or ""))
                self.contract_table.setItem(i, 3, QTableWidgetItem(r.contract_type or ""))
                self.contract_table.setItem(i, 4, QTableWidgetItem(r.risk_tags or ""))
                self.contract_table.setItem(i, 5, QTableWidgetItem(r.status))
        finally:
            session.close()
