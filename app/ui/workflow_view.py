"""工作流可视化页面 — 当前步骤/进度/历史（可折叠运行中项目）"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QProgressBar, QFrame,
    QGroupBox, QGridLayout, QMessageBox, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QTimer
from PySide6.QtGui import QFont, QColor, QPainter, QPixmap

from app.database.connection import DatabaseManager
from app.database.models import WorkflowInstance, WorkflowDefinition, WorkflowStepLog, ChangeOrder


class CollapsibleSection(QWidget):
    """可折叠区域组件"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._collapsed = False
        self._content = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题按钮
        self.toggle_btn = QPushButton(f"▼ {title}")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 600;
                color: #1E293B;
                padding: 8px 4px;
            }
            QPushButton:hover {
                color: #EA580C;
            }
        """)
        self.toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self.toggle_btn)

        # 内容容器
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(8)
        layout.addWidget(self._content_container)

    def set_content(self, widget: QWidget):
        """设置内容组件"""
        self._content_layout.addWidget(widget)
        self._content = widget

    def get_content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._content_container.setVisible(not self._collapsed)
        self.toggle_btn.setText(f"{'▶' if self._collapsed else '▼'} {self.toggle_btn.text()[1:]}")

    def collapse(self):
        self._collapsed = True
        self._content_container.setVisible(False)
        self.toggle_btn.setText(f"▶ {self.toggle_btn.text()[1:]}")

    def expand(self):
        self._collapsed = False
        self._content_container.setVisible(True)
        self.toggle_btn.setText(f"▼ {self.toggle_btn.text()[1:]}")


class WorkflowStepWidget(QFrame):
    """工作流步骤节点组件"""

    def __init__(self, step_name: str, step_index: int, current_index: int,
                 status: str = "pending", is_auto: bool = False):
        super().__init__()
        self.setObjectName("stepWidget")
        self.setFixedHeight(90)
        self.setMinimumWidth(140)

        if step_index < current_index:
            bg = "#DCFCE7"
            border = "#16A34A"
            icon = "✅"
        elif step_index == current_index:
            bg = "#DBEAFE"
            border = "#2563EB"
            icon = "▶️"
        elif status == "rejected":
            bg = "#FEE2E2"
            border = "#DC2626"
            icon = "❌"
        else:
            bg = "#F8FAFC"
            border = "#CBD5E1"
            icon = "⏳"

        self.setStyleSheet(f"""
            #stepWidget {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 8px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16px;")
        header.addWidget(icon_label)

        step_num = QLabel(f"步骤 {step_index + 1}")
        step_num.setStyleSheet(f"font-size: 11px; color: {border}; font-weight: 600;")
        header.addWidget(step_num)
        header.addStretch()

        if is_auto:
            auto_label = QLabel("🤖")
            auto_label.setStyleSheet("font-size: 12px;")
            auto_label.setToolTip("AI自动执行")
            header.addWidget(auto_label)

        layout.addLayout(header)

        name_label = QLabel(step_name)
        name_label.setWordWrap(True)
        name_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: #1E293B;")
        layout.addWidget(name_label)


class WorkflowView(QWidget):
    """工作流可视化页面"""

    def __init__(self, db):
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
        title = QLabel("⚙️ 工作流自动化")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("变更签证审批流 · 质量整改闭环 · 验收闭环")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        # 使用 QSplitter 让上下两部分平分空间
        splitter = QSplitter(Qt.Vertical)

        # ── 上半部分：可折叠的运行中工作流 ──
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.collapsible = CollapsibleSection("运行中的工作流")
        self.card_container = QVBoxLayout()
        self.card_container.setSpacing(12)

        # 用 QScrollArea 包装卡片，防止卡片过多压垮布局
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #F1F5F9;
                width: 6px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                border-radius: 3px;
                min-height: 30px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setLayout(self.card_container)
        scroll_area.setWidget(scroll_content)

        self.collapsible.get_content_layout().addWidget(scroll_area)
        top_layout.addWidget(self.collapsible)

        splitter.addWidget(top_widget)

        # ── 下半部分：工作流定义 ──
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        def_label = QLabel("工作流定义")
        def_label.setProperty("heading", "true")
        bottom_layout.addWidget(def_label)

        self.def_table = QTableWidget(0, 6)
        self.def_table.setHorizontalHeaderLabels(["ID", "名称", "业务类型", "步骤数", "状态", "操作"])
        self.def_table.horizontalHeader().setStretchLastSection(True)
        self.def_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.def_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.def_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.def_table.setAlternatingRowColors(True)
        self.def_table.verticalHeader().setVisible(False)
        bottom_layout.addWidget(self.def_table, stretch=1)

        # 操作按钮
        toolbar = QHBoxLayout()
        btn_init_change = QPushButton("初始化变更签证审批流")
        btn_init_change.clicked.connect(self._init_change_workflow)
        toolbar.addWidget(btn_init_change)

        btn_init_quality = QPushButton("初始化质量整改闭环")
        btn_init_quality.clicked.connect(self._init_quality_workflow)
        toolbar.addWidget(btn_init_quality)

        btn_del_workflow = QPushButton("🗑️ 删除工作流")
        btn_del_workflow.clicked.connect(self._del_workflow)
        toolbar.addWidget(btn_del_workflow)

        toolbar.addStretch()
        bottom_layout.addLayout(toolbar)

        splitter.addWidget(bottom_widget)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter, stretch=1)

    def _refresh(self):
        session = self.db.get_session()
        try:
            # 刷新工作流定义
            defs = session.query(WorkflowDefinition).all()
            self.def_table.setRowCount(len(defs))
            for i, wf in enumerate(defs):
                self.def_table.setItem(i, 0, QTableWidgetItem(str(wf.id)))
                self.def_table.setItem(i, 1, QTableWidgetItem(wf.name or ""))
                self.def_table.setItem(i, 2, QTableWidgetItem(wf.biz_type or ""))
                import json
                steps = json.loads(wf.steps) if wf.steps else []
                self.def_table.setItem(i, 3, QTableWidgetItem(str(len(steps))))
                self.def_table.setItem(i, 4, QTableWidgetItem("活跃" if wf.is_active else "停用"))
                self.def_table.setItem(i, 5, QTableWidgetItem(f"ID:{wf.id}"))

            # 刷新运行中的实例
            instances = session.query(WorkflowInstance).filter(
                WorkflowInstance.status == "running"
            ).order_by(WorkflowInstance.created_at.desc()).limit(5).all()

            # 清空卡片容器
            while self.card_container.count():
                item = self.card_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            if not instances:
                empty = QLabel("暂无运行中的工作流，请先初始化或创建")
                empty.setStyleSheet("color: #94A3B8; padding: 20px;")
                empty.setAlignment(Qt.AlignCenter)
                self.card_container.addWidget(empty)
            else:
                for inst in instances:
                    card = self._create_instance_card(inst)
                    self.card_container.addWidget(card)

        finally:
            session.close()

    def _create_instance_card(self, instance):
        card = QFrame()
        card.setObjectName("wfCard")
        card.setStyleSheet("""
            #wfCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 16px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        header = QHBoxLayout()
        name_label = QLabel(f"{instance.biz_type} 实例 #{instance.biz_record_id}")
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1E293B;")
        header.addWidget(name_label)

        status_label = QLabel("运行中")
        status_label.setStyleSheet(
            "background-color: #DBEAFE; color: #2563EB; padding: 2px 8px; "
            "border-radius: 4px; font-size: 11px; font-weight: 600;"
        )
        header.addWidget(status_label)
        header.addStretch()

        current_label = QLabel(f"当前步骤: {instance.current_step}")
        current_label.setStyleSheet("color: #64748B; font-size: 12px;")
        header.addWidget(current_label)

        layout.addLayout(header)

        session = self.db.get_session()
        try:
            wf_def = session.query(WorkflowDefinition).get(instance.workflow_def_id)
            if wf_def and wf_def.steps:
                import json
                steps = json.loads(wf_def.steps)

                progress = (instance.current_step_index + 1) / len(steps) * 100
                progress_bar = QProgressBar()
                progress_bar.setRange(0, 100)
                progress_bar.setValue(int(progress))
                progress_bar.setFormat(f"步骤 {instance.current_step_index + 1}/{len(steps)} ({int(progress)}%)")
                progress_bar.setFixedHeight(20)
                layout.addWidget(progress_bar)

                steps_layout = QHBoxLayout()
                steps_layout.setSpacing(4)

                step_logs = session.query(WorkflowStepLog).filter(
                    WorkflowStepLog.instance_id == instance.id
                ).all()
                completed_steps = {log.step_index for log in step_logs}

                for i, step in enumerate(steps):
                    step_widget = WorkflowStepWidget(
                        step_name=step.get("name", f"步骤{i+1}"),
                        step_index=i,
                        current_index=instance.current_step_index,
                        status="completed" if i in completed_steps else "pending",
                        is_auto=step.get("type", "") == "auto",
                    )
                    steps_layout.addWidget(step_widget)

                    if i < len(steps) - 1:
                        arrow = QLabel("→")
                        arrow.setStyleSheet("font-size: 20px; color: #94A3B8;")
                        arrow.setAlignment(Qt.AlignCenter)
                        steps_layout.addWidget(arrow)

                layout.addLayout(steps_layout)
        finally:
            session.close()

        return card

    def _init_change_workflow(self):
        from app.modules.workflow_engine import workflow
        wf_id = workflow.init_change_order_workflow()
        self._refresh()
        QMessageBox.information(self, "成功", f"变更签证审批流已初始化 (ID={wf_id})")

    def _init_quality_workflow(self):
        from app.modules.workflow_engine import workflow
        wf_id = workflow.init_quality_workflow()
        self._refresh()
        QMessageBox.information(self, "成功", f"质量整改闭环已初始化 (ID={wf_id})")

    def _del_workflow(self):
        """删除选中的工作流定义"""
        row = self.def_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选中一个工作流定义")
            return
        wf_id = int(self.def_table.item(row, 0).text())
        wf_name = self.def_table.item(row, 1).text()
        reply = QMessageBox.question(self, "确认删除",
            f"确定要删除工作流「{wf_name}」？",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = self.db.get_session()
            try:
                from app.database.models import WorkflowDefinition, WorkflowInstance, WorkflowStepLog
                instances = session.query(WorkflowInstance).filter(
                    WorkflowInstance.workflow_def_id == wf_id).all()
                for inst in instances:
                    session.query(WorkflowStepLog).filter(
                        WorkflowStepLog.instance_id == inst.id).delete()
                    session.delete(inst)
                wf = session.query(WorkflowDefinition).get(wf_id)
                if wf:
                    session.delete(wf)
                session.commit()
                self._refresh()
            finally:
                session.close()