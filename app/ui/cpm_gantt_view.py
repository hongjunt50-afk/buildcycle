"""CPM 进度计划 Gantt 图可视化"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFrame, QScrollArea,
    QGroupBox, QInputDialog, QMessageBox, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath

from app.database.connection import DatabaseManager
from app.database.models import ProgressPlan, TaskDependency
from datetime import datetime, date, timedelta


class GanttChartWidget(QWidget):
    """Gantt 图绘制组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.day_width = 30
        self.row_height = 32
        self.header_height = 40
        self.padding_left = 160
        self.padding_top = self.header_height
        self.setMinimumHeight(200)

    def set_tasks(self, tasks: list):
        """设置任务数据
        tasks: [{id, name, start, end, duration, float, critical, progress}]
        """
        self.tasks = tasks
        self.update()

    def paintEvent(self, event):
        if not self.tasks:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算总天数
        max_end = max(t.get("end", 0) for t in self.tasks) + 2
        total_width = self.padding_left + max_end * self.day_width
        total_height = self.padding_top + len(self.tasks) * self.row_height + 20
        self.setMinimumWidth(total_width)
        self.setMinimumHeight(total_height)

        # 绘制背景
        painter.fillRect(0, 0, total_width, total_height, QColor("#F8FAFC"))

        # 绘制表头（天数）
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.setFont(QFont("Source Sans 3", 9))
        for day in range(max_end):
            x = self.padding_left + day * self.day_width
            painter.drawText(QRectF(x, 0, self.day_width, self.header_height - 5),
                            Qt.AlignCenter, str(day))
            # 竖线
            painter.setPen(QPen(QColor("#E2E8F0"), 0.5))
            painter.drawLine(x, self.header_height, x, total_height)

        # 绘制任务
        painter.setFont(QFont("Source Sans 3", 10))
        for i, task in enumerate(self.tasks):
            y = self.padding_top + i * self.row_height

            # 任务名称
            painter.setPen(QPen(QColor("#1E293B"), 1))
            name = task.get("name", "")
            painter.drawText(QRectF(5, y, self.padding_left - 10, self.row_height),
                            Qt.AlignVCenter | Qt.AlignLeft, name)

            # Gantt 条
            start = task.get("start", 0)
            end = task.get("end", 0)
            duration = task.get("duration", 1)
            is_critical = task.get("critical", False)
            progress = task.get("progress", 0)
            float_days = task.get("float", 0)

            bar_x = self.padding_left + start * self.day_width + 2
            bar_w = duration * self.day_width - 4
            bar_h = self.row_height - 6
            bar_y = y + 3

            # 绘制浮动时间（如果有）
            if float_days and float_days > 0:
                float_x = bar_x + bar_w + 2
                float_w = float_days * self.day_width - 4
                painter.setBrush(QBrush(QColor("#F1F5F9")))
                painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.DashLine))
                painter.drawRect(int(float_x), int(bar_y), int(float_w), int(bar_h))

            # 绘制任务条
            if is_critical:
                bar_color = QColor("#EA580C")  # 关键路径：橙色
            else:
                bar_color = QColor("#64748B")  # 非关键：灰色

            painter.setBrush(QBrush(bar_color))
            painter.setPen(QPen(bar_color.darker(120), 1))
            painter.drawRoundedRect(int(bar_x), int(bar_y), int(bar_w), int(bar_h), 4, 4)

            # 绘制进度填充
            if progress > 0:
                progress_w = bar_w * progress / 100
                painter.setBrush(QBrush(QColor("#16A34A")))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(bar_x), int(bar_y), int(progress_w), int(bar_h), 4, 4)

            # 绘制天数标签
            painter.setPen(QPen(QColor("#FFFFFF"), 1))
            painter.setFont(QFont("Source Sans 3", 9))
            painter.drawText(QRectF(int(bar_x), int(bar_y), int(bar_w), int(bar_h)),
                            Qt.AlignCenter, f"{duration}d")

            # 关键路径标记
            if is_critical:
                painter.setPen(QPen(QColor("#EA580C"), 1))
                painter.setFont(QFont("Source Sans 3", 8))
                painter.drawText(QRectF(int(bar_x + bar_w + 4), int(bar_y), 60, int(bar_h)),
                                Qt.AlignVCenter | Qt.AlignLeft, "🔴 关键")

            # 绘制依赖箭头
            if i < len(self.tasks) - 1:
                next_task = self.tasks[i + 1]
                if task.get("id") and next_task.get("id"):
                    # 如果有依赖，画箭头
                    pass  # 简化处理


class CpmGanttView(QWidget):
    """CPM 进度计划 + Gantt 图"""

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
        title = QLabel("📅 进度计划管理 (CPM + Gantt)")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("关键路径分析 · 四种依赖类型 · 二次验算 · 进度跟踪")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()

        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self._refresh)
        header.addWidget(btn_refresh)

        layout.addLayout(header)

        # 工具栏
        toolbar = QHBoxLayout()

        btn_add = QPushButton("＋ 新增任务")
        btn_add.clicked.connect(self._on_add_task)
        toolbar.addWidget(btn_add)

        btn_calc = QPushButton("🧮 计算 CPM")
        btn_calc.clicked.connect(self._on_calc_cpm)
        toolbar.addWidget(btn_calc)

        btn_add_dep = QPushButton("🔗 添加依赖")
        btn_add_dep.clicked.connect(self._on_add_dependency)
        toolbar.addWidget(btn_add_dep)

        btn_level = QPushButton("⚖️ 资源平衡")
        btn_level.clicked.connect(self._on_level_resources)
        toolbar.addWidget(btn_level)

        toolbar.addStretch()

        # 分析结果
        self.cpm_result_label = QLabel("")
        self.cpm_result_label.setStyleSheet("color: #1E293B; font-weight: 600;")
        toolbar.addWidget(self.cpm_result_label)

        layout.addLayout(toolbar)

        # 任务表格
        self.task_table = QTableWidget(0, 8)
        self.task_table.setHorizontalHeaderLabels(["ID", "任务名称", "工期", "ES", "EF", "LS", "LF", "浮动"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.verticalHeader().setVisible(False)
        layout.addWidget(self.task_table)

        # Gantt 图
        gantt_label = QLabel("Gantt 图")
        gantt_label.setProperty("heading", "true")
        layout.addWidget(gantt_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #E2E8F0; border-radius: 6px; background: #FFFFFF; }")

        self.gantt_widget = GanttChartWidget()
        scroll.setWidget(self.gantt_widget)
        layout.addWidget(scroll, stretch=1)

    def _refresh(self):
        """刷新数据"""
        session = self.db.get_session()
        try:
            tasks = session.query(ProgressPlan).order_by(ProgressPlan.id).all()
            self.task_table.setRowCount(len(tasks))
            for i, t in enumerate(tasks):
                self.task_table.setItem(i, 0, QTableWidgetItem(str(t.id)))
                self.task_table.setItem(i, 1, QTableWidgetItem(t.task_name or ""))
                self.task_table.setItem(i, 2, QTableWidgetItem(str(t.delay_days or 0)))
                self.task_table.setItem(i, 3, QTableWidgetItem(""))
                self.task_table.setItem(i, 4, QTableWidgetItem(""))
                self.task_table.setItem(i, 5, QTableWidgetItem(""))
                self.task_table.setItem(i, 6, QTableWidgetItem(""))
                self.task_table.setItem(i, 7, QTableWidgetItem(""))

            # 更新 Gantt 数据
            gantt_data = []
            for i, t in enumerate(tasks):
                gantt_data.append({
                    "id": t.id,
                    "name": t.task_name or f"任务{t.id}",
                    "start": i * 2,
                    "end": i * 2 + (t.delay_days or 1) if t.delay_days else 1,
                    "duration": t.delay_days or 1,
                    "float": 0,
                    "critical": False,
                    "progress": t.progress_pct or 0,
                })
            self.gantt_widget.set_tasks(gantt_data)

            self.cpm_result_label.setText(f"共 {len(tasks)} 个任务 | 点击「计算 CPM」分析关键路径")

        finally:
            session.close()

    def _on_add_task(self):
        """新增任务"""
        dialog = QDialog(self)
        dialog.setWindowTitle("新增任务")
        dialog.resize(400, 300)

        layout = QFormLayout(dialog)
        name_input = QLineEdit()
        name_input.setPlaceholderText("任务名称")
        layout.addRow("名称：", name_input)

        dur_input = QDoubleSpinBox()
        dur_input.setRange(1, 999)
        dur_input.setSuffix(" 天")
        layout.addRow("工期：", dur_input)

        proj_input = QLineEdit()
        proj_input.setPlaceholderText("项目名称")
        layout.addRow("项目：", proj_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            session = self.db.get_session()
            try:
                task = ProgressPlan(
                    project_name=proj_input.text().strip() or "默认项目",
                    task_name=name_input.text().strip(),
                    delay_days=int(dur_input.value()),
                )
                session.add(task)
                session.commit()
                self._refresh()
            finally:
                session.close()

    def _on_add_dependency(self):
        """添加依赖关系"""
        rows = self.task_table.selectionModel().selectedRows()
        if len(rows) < 2:
            QMessageBox.warning(self, "提示", "请先选中两个任务（按住Ctrl多选）")
            return

        pred_id = int(self.task_table.item(rows[0].row(), 0).text())
        succ_id = int(self.task_table.item(rows[1].row(), 0).text())

        dep_type, ok = QInputDialog.getItem(
            self, "依赖类型", "选择依赖类型:",
            ["FS (完成-开始)", "SS (开始-开始)", "FF (完成-完成)", "SF (开始-完成)"],
            0, False
        )
        if not ok:
            return

        type_map = {"FS (完成-开始)": "FS", "SS (开始-开始)": "SS", "FF (完成-完成)": "FF", "SF (开始-完成)": "SF"}

        session = self.db.get_session()
        try:
            dep = TaskDependency(
                project_name="默认项目",
                predecessor_id=pred_id,
                successor_id=succ_id,
                dep_type=type_map.get(dep_type, "FS"),
            )
            session.add(dep)
            session.commit()
            QMessageBox.information(self, "成功", f"已添加依赖: {dep_type}")
        finally:
            session.close()

    def _on_calc_cpm(self):
        """计算 CPM"""
        session = self.db.get_session()
        try:
            from app.modules.cpm_engine import CPMEngine, CPMTask

            tasks = session.query(ProgressPlan).all()
            if not tasks:
                QMessageBox.warning(self, "提示", "没有任务数据")
                return

            engine = CPMEngine()
            for t in tasks:
                engine.add_task(CPMTask(t.id, t.task_name or f"任务{t.id}", t.delay_days or 1))

            # 加载依赖
            deps = session.query(TaskDependency).all()
            for d in deps:
                engine.add_dependency(d.predecessor_id, d.successor_id, d.dep_type or "FS", d.lag_days or 0)

            result = engine.calculate_with_verify()

            # 更新表格
            for tid, info in result["tasks"].items():
                for row in range(self.task_table.rowCount()):
                    if int(self.task_table.item(row, 0).text()) == tid:
                        self.task_table.setItem(row, 3, QTableWidgetItem(str(info["es"])))
                        self.task_table.setItem(row, 4, QTableWidgetItem(str(info["ef"])))
                        self.task_table.setItem(row, 5, QTableWidgetItem(str(info["ls"])))
                        self.task_table.setItem(row, 6, QTableWidgetItem(str(info["lf"])))
                        self.task_table.setItem(row, 7, QTableWidgetItem(str(info["float"])))

                        # 标记关键路径
                        if info["critical"]:
                            for col in range(8):
                                item = self.task_table.item(row, col)
                                if item:
                                    item.setBackground(QBrush(QColor("#FEF3C7")))

            # 更新 Gantt
            gantt_data = []
            for tid, info in result["tasks"].items():
                gantt_data.append({
                    "id": tid,
                    "name": info["name"],
                    "start": info["es"],
                    "end": info["ef"],
                    "duration": info.get("duration", 1),
                    "float": info.get("float", 0),
                    "critical": info.get("critical", False),
                    "progress": 0,
                })
            self.gantt_widget.set_tasks(gantt_data)

            # 显示结果
            cp = result["critical_path"]
            cp_names = " → ".join(name for _, name in cp)
            status = "✅" if result["verify_passed"] else "⚠️"
            self.cpm_result_label.setText(
                f"{status} 总工期: {result['total_duration']}天 | "
                f"关键路径: {cp_names} | "
                f"验算: {'通过' if result['verify_passed'] else '失败'}"
            )

        finally:
            session.close()

    def _on_level_resources(self):
        """资源平衡"""
        session = self.db.get_session()
        try:
            from app.modules.resource_leveling import ResourceLevelingEngine

            # 从 CPM 结果获取数据
            from app.modules.cpm_engine import CPMEngine, CPMTask

            tasks = session.query(ProgressPlan).all()
            if not tasks:
                QMessageBox.warning(self, "提示", "没有任务数据")
                return

            engine = CPMEngine()
            for t in tasks:
                engine.add_task(CPMTask(t.id, t.task_name or f"任务{t.id}", t.delay_days or 1))

            deps = session.query(TaskDependency).all()
            for d in deps:
                engine.add_dependency(d.predecessor_id, d.successor_id, d.dep_type or "FS", d.lag_days or 0)

            cpm_result = engine.calculate()

            # 资源平衡
            leveler = ResourceLevelingEngine()
            leveler.add_resource("默认资源", 5)

            for tid, info in cpm_result["tasks"].items():
                leveler.add_task(
                    task_id=tid,
                    name=info["name"],
                    duration=info.get("duration", 1),
                    es=info["es"],
                    ef=info["ef"],
                    ls=info["ls"],
                    lf=info["lf"],
                    is_critical=info.get("critical", False),
                    resource="默认资源",
                    resource_amount=1,
                )

            level_result = leveler.level()

            msg = f"资源平衡完成\n"
            msg += f"平衡状态: {'✅ 已平衡' if level_result['balanced'] else '⚠️ 未完全平衡'}\n"
            msg += f"移动次数: {level_result['moves_count']}\n"
            msg += f"迭代轮数: {level_result['iterations']}\n"

            if level_result["moves"]:
                msg += "\n移动详情:\n"
                for m in level_result["moves"]:
                    msg += f"  - {m['task_name']}: 从第{m['from']}天→第{m['to']}天\n"

            QMessageBox.information(self, "资源平衡结果", msg)

        finally:
            session.close()
