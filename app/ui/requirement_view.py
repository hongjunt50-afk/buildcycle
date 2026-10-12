"""需求与策划视图 — 卡片式列表"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QDialog,
    QFormLayout, QTextEdit, QLineEdit, QDoubleSpinBox, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt
from datetime import datetime

from app.database.connection import DatabaseManager
from app.database.models import ProjectRequirement


class RequirementDialog(QDialog):
    """新增/编辑需求对话框"""

    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle("新增需求" if record is None else "编辑需求")
        self.resize(640, 520)
        self.setMinimumWidth(500)
        self._setup_ui()
        if record:
            self._load_record()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        title = QLabel("项目需求录入")
        title.setProperty("heading", "true")
        layout.addWidget(title)

        form_widget = QFrame()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("例如：XX新城住宅小区项目")
        form_layout.addRow("项目名称：", self.project_name)

        self.owner_name = QLineEdit()
        self.owner_name.setPlaceholderText("业主单位名称")
        form_layout.addRow("业主名称：", self.owner_name)

        self.requirement_desc = QTextEdit()
        self.requirement_desc.setPlaceholderText("业主核心需求描述...")
        self.requirement_desc.setMaximumHeight(100)
        form_layout.addRow("需求描述：", self.requirement_desc)

        self.functional_reqs = QTextEdit()
        self.functional_reqs.setPlaceholderText("功能需求清单...")
        self.functional_reqs.setMaximumHeight(100)
        form_layout.addRow("功能需求：", self.functional_reqs)

        self.delivery_standard = QTextEdit()
        self.delivery_standard.setPlaceholderText("交付标准...")
        self.delivery_standard.setMaximumHeight(80)
        form_layout.addRow("交付标准：", self.delivery_standard)

        self.budget_limit = QDoubleSpinBox()
        self.budget_limit.setRange(0, 999999)
        self.budget_limit.setSuffix(" 万元")
        self.budget_limit.setSpecialValueText("未设置")
        form_layout.addRow("预算上限：", self.budget_limit)

        layout.addWidget(form_widget)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_record(self):
        self.project_name.setText(self.record.project_name or "")
        self.owner_name.setText(self.record.owner_name or "")
        self.requirement_desc.setPlainText(self.record.requirement_desc or "")
        self.functional_reqs.setPlainText(self.record.functional_reqs or "")
        self.delivery_standard.setPlainText(self.record.delivery_standard or "")
        self.budget_limit.setValue(self.record.budget_limit or 0)

    def get_data(self) -> dict:
        return {
            "project_name": self.project_name.text(),
            "owner_name": self.owner_name.text(),
            "requirement_desc": self.requirement_desc.toPlainText(),
            "functional_reqs": self.functional_reqs.toPlainText(),
            "delivery_standard": self.delivery_standard.toPlainText(),
            "budget_limit": self.budget_limit.value(),
        }


class RequirementView(QWidget):
    """需求与策划模块视图"""

    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题区
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("需求与策划")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("管理业主需求录入、可行性评估、项目策划书")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()
        layout.addLayout(header)

        # 操作栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        btn_add = QPushButton("＋ 新增需求")
        btn_add.clicked.connect(self._on_add)
        toolbar.addWidget(btn_add)

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self._refresh)
        toolbar.addWidget(btn_refresh)

        btn_delete = QPushButton("🗑️ 删除选中")
        btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(btn_delete)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "项目名称", "业主", "需求描述", "预算(万元)", "状态", "更新时间"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.doubleClicked.connect(self._on_edit)
        layout.addWidget(self.table)

    def _refresh(self):
        """刷新列表"""
        session = self.db.get_session()
        try:
            records = session.query(ProjectRequirement).order_by(ProjectRequirement.updated_at.desc()).all()
            self.table.setRowCount(len(records))
            for i, r in enumerate(records):
                self.table.setItem(i, 0, QTableWidgetItem(str(r.id)))
                self.table.setItem(i, 1, QTableWidgetItem(r.project_name or ""))
                self.table.setItem(i, 2, QTableWidgetItem(r.owner_name or ""))
                desc = (r.requirement_desc or "")[:60] + ("..." if len(r.requirement_desc or "") > 60 else "")
                self.table.setItem(i, 3, QTableWidgetItem(desc))
                self.table.setItem(i, 4, QTableWidgetItem(str(r.budget_limit or "")))

                status_map = {"draft": "草稿", "confirmed": "已确认"}
                status_item = QTableWidgetItem(status_map.get(r.status, r.status))
                if r.status == "confirmed":
                    status_item.setForeground(Qt.green)
                else:
                    status_item.setForeground(Qt.darkYellow)
                self.table.setItem(i, 5, status_item)

                self.table.setItem(i, 6, QTableWidgetItem(
                    r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else ""
                ))
        finally:
            session.close()

    def _on_add(self):
        dialog = RequirementDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            session = self.db.get_session()
            try:
                record = ProjectRequirement(**data)
                session.add(record)
                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        record_id = int(self.table.item(row, 0).text())
        session = self.db.get_session()
        try:
            record = session.query(ProjectRequirement).get(record_id)
            if record:
                dialog = RequirementDialog(self, record)
                if dialog.exec() == QDialog.Accepted:
                    data = dialog.get_data()
                    for k, v in data.items():
                        setattr(record, k, v)
                    record.updated_at = datetime.now()
                    session.commit()
                    self._refresh()
        finally:
            session.close()

    def _on_delete(self):
        """删除选中需求"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中要删除的需求")
            return

        record_id = int(self.table.item(row, 0).text())
        record_name = self.table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除需求「{record_name}」吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                record = session.query(ProjectRequirement).get(record_id)
                if record:
                    session.delete(record)
                    session.commit()
                    self._refresh()
            finally:
                session.close()
