"""BOQ 工程量清单编辑界面"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox, QTextEdit,
    QDialogButtonBox, QComboBox, QFrame, QSplitter, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QTabWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QBrush

from app.database.connection import DatabaseManager
from app.database.models import BoqSection, BoqItem
from sqlalchemy.orm import joinedload


class BoqSectionDialog(QDialog):
    """添加/编辑章节对话框"""

    def __init__(self, parent=None, section=None):
        super().__init__(parent)
        self.section = section
        self.setWindowTitle("章节" if section else "新增章节")
        self.resize(400, 200)

        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("如：01.01")
        layout.addRow("章节编号：", self.code_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：土方工程")
        layout.addRow("章节名称：", self.name_input)

        if section:
            self.code_input.setText(section.section_code or "")
            self.name_input.setText(section.section_name or "")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        return {
            "section_code": self.code_input.text().strip(),
            "section_name": self.name_input.text().strip(),
        }


class BoqItemDialog(QDialog):
    """添加/编辑清单条目对话框"""

    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("编辑清单项" if item else "新增清单项")
        self.resize(500, 350)

        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.item_code = QLineEdit()
        self.item_code.setPlaceholderText("清单编号")
        layout.addRow("编号：", self.item_code)

        self.item_name = QLineEdit()
        self.item_name.setPlaceholderText("清单名称，如：挖一般土方")
        layout.addRow("名称：", self.item_name)

        self.unit = QComboBox()
        self.unit.addItems(["m³", "m²", "m", "个", "项", "t", "kg", "套", "处"])
        self.unit.setEditable(True)
        layout.addRow("单位：", self.unit)

        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0, 999999)
        self.quantity.setDecimals(2)
        layout.addRow("数量：", self.quantity)

        self.unit_price = QDoubleSpinBox()
        self.unit_price.setRange(0, 999999)
        self.unit_price.setDecimals(2)
        self.unit_price.setPrefix("¥ ")
        layout.addRow("单价：", self.unit_price)

        self.remark = QLineEdit()
        self.remark.setPlaceholderText("备注")
        layout.addRow("备注：", self.remark)

        # 自动计算合价显示
        self.total_label = QLabel("合价：¥ 0.00")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #EA580C;")
        layout.addRow(self.total_label)

        self.quantity.valueChanged.connect(self._calc_total)
        self.unit_price.valueChanged.connect(self._calc_total)

        if item:
            self.item_code.setText(item.item_code or "")
            self.item_name.setText(item.item_name or "")
            idx = self.unit.findText(item.unit or "")
            if idx >= 0:
                self.unit.setCurrentIndex(idx)
            else:
                self.unit.setEditText(item.unit or "")
            self.quantity.setValue(item.quantity or 0)
            self.unit_price.setValue(item.unit_price or 0)
            self.remark.setText(item.remark or "")
            self._calc_total()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _calc_total(self):
        total = self.quantity.value() * self.unit_price.value()
        self.total_label.setText(f"合价：¥ {total:,.2f}")

    def get_data(self) -> dict:
        return {
            "item_code": self.item_code.text().strip(),
            "item_name": self.item_name.text().strip(),
            "unit": self.unit.currentText(),
            "quantity": self.quantity.value(),
            "unit_price": self.unit_price.value(),
            "total_price": round(self.quantity.value() * self.unit_price.value(), 2),
            "remark": self.remark.text().strip(),
        }


class BoqView(QWidget):
    """BOQ 工程量清单编辑界面"""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_project = ""
        self.current_section_id = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题区
        header = QHBoxLayout()
        title_group = QVBoxLayout()
        title = QLabel("📋 工程量清单 (BOQ)")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("清单章节管理 · 条目编辑 · 自动计算 · 导出")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()

        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(200)
        self.project_combo.setPlaceholderText("选择项目...")
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        header.addWidget(QLabel("项目："))
        header.addWidget(self.project_combo)

        layout.addLayout(header)

        # 工具栏
        toolbar = QHBoxLayout()

        btn_add_section = QPushButton("📁 新增章节")
        btn_add_section.clicked.connect(self._on_add_section)
        toolbar.addWidget(btn_add_section)

        btn_add_item = QPushButton("＋ 新增清单项")
        btn_add_item.clicked.connect(self._on_add_item)
        toolbar.addWidget(btn_add_item)

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self._refresh)
        toolbar.addWidget(btn_refresh)

        btn_export = QPushButton("📤 导出 Excel")
        btn_export.clicked.connect(self._on_export)
        toolbar.addWidget(btn_export)

        toolbar.addStretch()

        # 汇总信息
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #1E293B; font-weight: 600;")
        toolbar.addWidget(self.summary_label)

        layout.addLayout(toolbar)

        # 分割：左侧章节树 + 右侧清单项
        splitter = QSplitter(Qt.Horizontal)

        # 左侧章节树
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("清单章节")
        left_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        left_layout.addWidget(left_label)

        self.section_tree = QTreeWidget()
        self.section_tree.setHeaderLabels(["章节名称", "编号", "小计"])
        self.section_tree.setColumnWidth(0, 200)
        self.section_tree.setColumnWidth(1, 80)
        self.section_tree.setAlternatingRowColors(True)
        self.section_tree.setMinimumWidth(300)
        self.section_tree.itemClicked.connect(self._on_section_clicked)
        left_layout.addWidget(self.section_tree)

        splitter.addWidget(left_widget)

        # 右侧清单项
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        right_label = QLabel("清单条目")
        right_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569;")
        right_layout.addWidget(right_label)

        self.item_table = QTableWidget(0, 8)
        self.item_table.setHorizontalHeaderLabels(["ID", "编号", "名称", "单位", "数量", "单价", "合价", "备注"])
        self.item_table.horizontalHeader().setStretchLastSection(True)
        self.item_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.item_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.item_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.item_table.setAlternatingRowColors(True)
        self.item_table.verticalHeader().setVisible(False)
        self.item_table.doubleClicked.connect(self._on_edit_item)
        right_layout.addWidget(self.item_table)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 500])

        layout.addWidget(splitter)

        # 底部工具
        bottom_toolbar = QHBoxLayout()

        btn_del_section = QPushButton("删除章节")
        btn_del_section.clicked.connect(self._on_delete_section)
        bottom_toolbar.addWidget(btn_del_section)

        btn_del_item = QPushButton("删除清单项")
        btn_del_item.clicked.connect(self._on_delete_item)
        bottom_toolbar.addWidget(btn_del_item)

        bottom_toolbar.addStretch()

        # 总计
        self.grand_total_label = QLabel("")
        self.grand_total_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #EA580C;")
        bottom_toolbar.addWidget(self.grand_total_label)

        layout.addLayout(bottom_toolbar)

        self._load_projects()

    def _load_projects(self):
        """加载项目列表"""
        session = self.db.get_session()
        try:
            projects = session.query(BoqSection.project_name).distinct().all()
            # 添加需求模块的项目
            from app.database.models import ProjectRequirement
            reqs = session.query(ProjectRequirement.project_name).filter(
                ProjectRequirement.project_name.isnot(None)
            ).all()

            all_projects = set()
            for p in projects:
                if p[0]:
                    all_projects.add(p[0])
            for p in reqs:
                if p[0]:
                    all_projects.add(p[0])

            self.project_combo.clear()
            self.project_combo.addItem("")
            for p in sorted(all_projects):
                self.project_combo.addItem(p)
        finally:
            session.close()

    def _on_project_changed(self, project: str):
        """切换项目"""
        self.current_project = project
        self._refresh()

    def _refresh(self):
        """刷新数据"""
        if not self.current_project:
            self.section_tree.clear()
            self.item_table.setRowCount(0)
            self.summary_label.setText("")
            self.grand_total_label.setText("")
            return

        session = self.db.get_session()
        try:
            # 加载章节树
            self.section_tree.clear()
            sections = session.query(BoqSection).filter(
                BoqSection.project_name == self.current_project,
                BoqSection.parent_id.is_(None)
            ).order_by(BoqSection.sort_order).all()

            for sec in sections:
                item = QTreeWidgetItem([sec.section_name, sec.section_code or "", f"¥{sec.subtotal:,.2f}" if sec.subtotal else ""])
                item.setData(0, Qt.UserRole, sec.id)
                self.section_tree.addTopLevelItem(item)

                # 加载子章节
                children = session.query(BoqSection).filter(
                    BoqSection.parent_id == sec.id
                ).order_by(BoqSection.sort_order).all()
                for child in children:
                    child_item = QTreeWidgetItem([child.section_name, child.section_code or "", f"¥{child.subtotal:,.2f}" if child.subtotal else ""])
                    child_item.setData(0, Qt.UserRole, child.id)
                    item.addChild(child_item)

            # 计算总计
            all_items = session.query(BoqItem).join(BoqSection).filter(
                BoqSection.project_name == self.current_project
            ).all()
            grand_total = sum(item.total_price or 0 for item in all_items)
            count = len(all_items)

            self.summary_label.setText(f"共 {count} 项")
            self.grand_total_label.setText(f"💰 总计：¥ {grand_total:,.2f}")

            # 加载清单项
            if self.current_section_id:
                self._load_items(session)

        finally:
            session.close()

    def _on_section_clicked(self, item, column):
        """选中章节"""
        section_id = item.data(0, Qt.UserRole)
        if section_id:
            self.current_section_id = section_id
            session = self.db.get_session()
            try:
                self._load_items(session)
            finally:
                session.close()

    def _load_items(self, session):
        """加载清单项"""
        items = session.query(BoqItem).filter(
            BoqItem.section_id == self.current_section_id
        ).order_by(BoqItem.id).all()

        self.item_table.setRowCount(len(items))
        for i, item in enumerate(items):
            self.item_table.setItem(i, 0, QTableWidgetItem(str(item.id)))
            self.item_table.setItem(i, 1, QTableWidgetItem(item.item_code or ""))
            self.item_table.setItem(i, 2, QTableWidgetItem(item.item_name or ""))
            self.item_table.setItem(i, 3, QTableWidgetItem(item.unit or ""))
            self.item_table.setItem(i, 4, QTableWidgetItem(f"{item.quantity:,.2f}" if item.quantity else ""))
            self.item_table.setItem(i, 5, QTableWidgetItem(f"¥{item.unit_price:,.2f}" if item.unit_price else ""))
            self.item_table.setItem(i, 6, QTableWidgetItem(f"¥{item.total_price:,.2f}" if item.total_price else ""))
            self.item_table.setItem(i, 7, QTableWidgetItem(item.remark or ""))

    def _on_add_section(self):
        """新增章节"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择一个项目")
            return

        dialog = BoqSectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            session = self.db.get_session()
            try:
                sec = BoqSection(
                    project_name=self.current_project,
                    section_code=data["section_code"],
                    section_name=data["section_name"],
                )
                session.add(sec)
                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_add_item(self):
        """新增清单项"""
        if not self.current_section_id:
            QMessageBox.warning(self, "提示", "请先在左侧选中一个章节")
            return

        dialog = BoqItemDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            session = self.db.get_session()
            try:
                item = BoqItem(
                    section_id=self.current_section_id,
                    **data
                )
                session.add(item)
                session.flush()   # 让新条目进入本次查询范围

                # 章节小计 = Σ条目合价（boq_engine 单一口径）
                from app.modules.boq_engine import recompute_section
                recompute_section(session, self.current_section_id)

                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_edit_item(self):
        """编辑清单项"""
        row = self.item_table.currentRow()
        if row < 0:
            return

        item_id = int(self.item_table.item(row, 0).text())
        session = self.db.get_session()
        try:
            item = session.query(BoqItem).get(item_id)
            if item:
                dialog = BoqItemDialog(self, item)
                if dialog.exec() == QDialog.Accepted:
                    data = dialog.get_data()
                    for k, v in data.items():
                        setattr(item, k, v)
                    session.commit()
                    self._refresh()
        finally:
            session.close()

    def _on_delete_section(self):
        """删除章节"""
        selected = self.section_tree.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先在左侧选中一个章节")
            return

        section_id = selected[0].data(0, Qt.UserRole)
        reply = QMessageBox.question(self, "确认删除",
            "删除章节将同时删除其下的所有清单项，确定？",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                session.query(BoqItem).filter(
                    BoqItem.section_id == section_id
                ).delete()
                session.query(BoqSection).filter(
                    BoqSection.id == section_id
                ).delete()
                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_delete_item(self):
        """删除清单项"""
        row = self.item_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中一个清单项")
            return

        item_id = int(self.item_table.item(row, 0).text())
        reply = QMessageBox.question(self, "确认删除",
            "确定要删除此清单项？",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                item = session.query(BoqItem).get(item_id)
                section_id = item.section_id if item else None
                session.query(BoqItem).filter(
                    BoqItem.id == item_id
                ).delete()

                # 删除后小计同步回落（boq_engine 单一口径）
                if section_id is not None:
                    from app.modules.boq_engine import recompute_section
                    recompute_section(session, section_id)

                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_export(self):
        """导出 Excel"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择一个项目")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "导出工程量清单",
            f"BOQ_{self.current_project}.xlsx",
            "Excel (*.xlsx)"
        )
        if not path:
            return

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "工程量清单"

            ws.append(["编号", "名称", "单位", "数量", "单价", "合价", "备注"])

            session = self.db.get_session()
            try:
                sections = session.query(BoqSection).filter(
                    BoqSection.project_name == self.current_project
                ).order_by(BoqSection.sort_order).all()

                for sec in sections:
                    ws.append([f"[{sec.section_code}] {sec.section_name}"])
                    items = session.query(BoqItem).filter(
                        BoqItem.section_id == sec.id
                    ).order_by(BoqItem.id).all()
                    for item in items:
                        ws.append([
                            item.item_code, item.item_name, item.unit,
                            item.quantity, item.unit_price, item.total_price,
                            item.remark
                        ])
                    ws.append([f"章节小计: ¥{sec.subtotal:,.2f}"])
                    ws.append([])

            finally:
                session.close()

            wb.save(path)
            QMessageBox.information(self, "成功", f"已导出到: {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
