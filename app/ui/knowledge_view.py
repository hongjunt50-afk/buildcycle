"""知识库管理页面 — 上传/搜索/查看/删除"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QFileDialog, QMessageBox,
    QTextEdit, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QSplitter, QFrame, QTabWidget, QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.knowledge.knowledge_manager import knowledge
from app.knowledge.vector_store import VectorStore
from app.agent.agent_core import AgentBehavior


class AddKnowledgeDialog(QDialog):
    """添加知识对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加知识")
        self.resize(600, 500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("添加知识源")
        title.setProperty("heading", "true")
        layout.addWidget(title)

        tabs = QTabWidget()

        # Tab 1: 手动输入
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("知识名称，如：GB50300-2013")
        form.addRow("名称：", self.name_input)
        text_layout.addLayout(form)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("粘贴知识内容...")
        text_layout.addWidget(self.content_input)

        btn_text_save = QPushButton("保存到知识库")
        btn_text_save.clicked.connect(self._save_text)
        text_layout.addWidget(btn_text_save)

        tabs.addTab(text_widget, "✏️ 手动输入")

        # Tab 2: 上传文件
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)

        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #94A3B8; padding: 8px;")
        file_layout.addWidget(self.file_path_label)

        btn_select = QPushButton("📁 选择文件")
        btn_select.clicked.connect(self._select_file)
        file_layout.addWidget(btn_select)

        info = QLabel("支持格式：PDF、Word(.docx)、Excel(.xlsx)、TXT、Markdown、图片")
        info.setStyleSheet("color: #64748B; font-size: 12px;")
        info.setWordWrap(True)
        file_layout.addWidget(info)

        btn_file_save = QPushButton("上传并添加到知识库")
        btn_file_save.clicked.connect(self._save_file)
        file_layout.addWidget(btn_file_save)

        file_layout.addStretch()
        tabs.addTab(file_widget, "📄 上传文件")

        layout.addWidget(tabs)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

        self.selected_file = None

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "",
            "支持的文件 (*.pdf *.docx *.xlsx *.txt *.md *.jpg *.png);;所有文件 (*)"
        )
        if path:
            self.selected_file = path
            from pathlib import Path
            self.file_path_label.setText(f"已选择: {Path(path).name}")
            self.file_path_label.setStyleSheet("color: #16A34A; padding: 8px;")

    def _save_text(self):
        name = self.name_input.text().strip()
        content = self.content_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入知识名称")
            return
        if not content:
            QMessageBox.warning(self, "提示", "请输入知识内容")
            return
        knowledge.add_text(name, content)
        QMessageBox.information(self, "成功", f"知识「{name}」已添加到知识库")
        self.accept()

    def _save_file(self):
        if not self.selected_file:
            QMessageBox.warning(self, "提示", "请先选择文件")
            return
        result = knowledge.add_file(self.selected_file)
        if result["status"] == "ok":
            QMessageBox.information(self, "成功", result["message"])
            self.accept()
        else:
            QMessageBox.critical(self, "失败", result["message"])


class ChunkViewerDialog(QDialog):
    """知识源分块内容查看弹窗 — 完整内容 + 滚动条"""

    def __init__(self, source_name: str, chunks: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"知识内容 — {source_name}")
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info = QLabel(f"「{source_name}」共 {len(chunks)} 个分块，完整内容如下：")
        info.setProperty("subheading", "true")
        layout.addWidget(info)

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        parts = []
        for c in chunks:
            idx = c.get("chunk_index", 0)
            parts.append(f"─── 分块 {idx + 1} ───\n{c.get('content', '')}")
        viewer.setPlainText("\n\n".join(parts) if parts else "（无内容）")
        # 滚动条样式：可见、可拖拽
        viewer.setStyleSheet("""
            QTextEdit { border: 1px solid #E2E8F0; border-radius: 6px; font-size: 13px; }
            QScrollBar:vertical {
                background: #F1F5F9; width: 10px; border: none; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #94A3B8; border-radius: 5px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #64748B; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        layout.addWidget(viewer, stretch=1)

        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 复制全部内容")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(viewer.toPlainText()))
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


class KnowledgeView(QWidget):
    """知识库管理页面"""

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
        title = QLabel("📚 知识库管理")
        title.setProperty("heading", "true")
        title_group.addWidget(title)
        subtitle = QLabel("上传文件、手动输入知识、联网搜索结果自动缓存")
        subtitle.setProperty("subheading", "true")
        title_group.addWidget(subtitle)
        header.addLayout(title_group)
        header.addStretch()

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索知识库...")
        self.search_input.setMaximumWidth(300)
        self.search_input.returnPressed.connect(self._on_search)
        header.addWidget(self.search_input)

        btn_search = QPushButton("搜索")
        btn_search.clicked.connect(self._on_search)
        header.addWidget(btn_search)

        layout.addLayout(header)

        # 操作栏
        toolbar = QHBoxLayout()

        btn_add = QPushButton("＋ 添加知识")
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

        # 搜索结果显示
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color: #64748B;")
        layout.addWidget(self.result_label)

        # 分割：左侧知识源列表 + 右侧内容预览
        splitter = QSplitter(Qt.Horizontal)

        # 左侧知识源列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.source_table = QTableWidget(0, 5)
        self.source_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "分块数", "创建时间"])
        self.source_table.horizontalHeader().setStretchLastSection(True)
        self.source_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.source_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.source_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.source_table.setAlternatingRowColors(True)
        self.source_table.verticalHeader().setVisible(False)
        self.source_table.setMinimumWidth(400)
        self.source_table.setToolTip("双击任意行可查看该知识源的完整分块内容")
        self.source_table.doubleClicked.connect(self._on_source_double_clicked)
        left_layout.addWidget(self.source_table)

        splitter.addWidget(left_widget)

        # 右侧内容预览
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        preview_label = QLabel("内容预览（双击左侧知识源可展开完整内容）")
        preview_label.setProperty("heading", "true")
        right_layout.addWidget(preview_label)

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setPlaceholderText("选中一条知识源查看内容...")
        self.preview_area.setMaximumHeight(200)
        self.preview_area.setStyleSheet(self._scroll_style())
        right_layout.addWidget(self.preview_area)

        # AI问答区
        query_label = QLabel("💬 向知识库提问")
        query_label.setProperty("heading", "true")
        right_layout.addWidget(query_label)

        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("输入问题，AI会先查知识库，未命中再联网搜索（四川优先）...")
        self.query_input.setMaximumHeight(80)
        self.query_input.setStyleSheet(self._scroll_style())
        right_layout.addWidget(self.query_input)

        btn_query = QPushButton("🤖 AI 查询")
        btn_query.clicked.connect(self._on_ai_query)
        right_layout.addWidget(btn_query)

        self.answer_area = QTextEdit()
        self.answer_area.setReadOnly(True)
        self.answer_area.setPlaceholderText("AI回答将显示在这里...")
        self.answer_area.setStyleSheet(self._scroll_style())
        right_layout.addWidget(self.answer_area)

        splitter.addWidget(right_widget)
        splitter.setSizes([500, 400])

        layout.addWidget(splitter)

    def _scroll_style(self):
        """长内容区域的滚动条样式 — 全局统一、可见、可拖拽"""
        return """
            QTextEdit { border: 1px solid #E2E8F0; border-radius: 6px; }
            QScrollBar:vertical {
                background: #F1F5F9; width: 10px; border: none; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #94A3B8; border-radius: 5px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #64748B; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal {
                background: #F1F5F9; height: 10px; border: none; border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background: #94A3B8; border-radius: 5px; min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover { background: #64748B; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """

    def _refresh(self):
        """刷新知识源列表"""
        self._search_results = None   # 回到知识源模式
        sources = knowledge.list_sources()
        self.source_table.setRowCount(len(sources))
        for i, s in enumerate(sources):
            self.source_table.setItem(i, 0, QTableWidgetItem(str(s.get("id", ""))))
            self.source_table.setItem(i, 1, QTableWidgetItem(s.get("name", "")))
            type_map = {"manual": "手动输入", "file_upload": "文件上传", "web_search": "联网搜索"}
            self.source_table.setItem(i, 2, QTableWidgetItem(type_map.get(s.get("source_type", ""), s.get("source_type", ""))))
            self.source_table.setItem(i, 3, QTableWidgetItem(str(s.get("chunk_count", ""))))
            self.source_table.setItem(i, 4, QTableWidgetItem(s.get("created_at", "")[:10] if s.get("created_at") else ""))

        self.result_label.setText(f"共 {len(sources)} 个知识源")

        # 连接选中事件
        self.source_table.itemSelectionChanged.connect(self._on_source_selected)

    def _on_source_selected(self):
        """选中知识源时显示预览（前几个分块的完整内容，超出滚动查看）"""
        rows = self.source_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        source_id = self.source_table.item(row, 0).text()
        source_name = self.source_table.item(row, 1).text()

        try:
            chunks = VectorStore().get_chunks(source_name)
            if chunks:
                text = "\n\n".join(
                    f"─── 分块 {c['chunk_index'] + 1} ───\n{c['content']}" for c in chunks[:2]
                )
                more = len(chunks) - 2
                if more > 0:
                    text += f"\n\n……还有 {more} 个分块，双击该行查看完整内容"
                self.preview_area.setPlainText(text)
            else:
                self.preview_area.setPlainText("(无预览内容)")
        except Exception:
            self.preview_area.setPlainText("(预览加载失败)")

    def _on_source_double_clicked(self, index):
        """双击知识源：弹窗展示全部分块的完整内容"""
        row = index.row()
        name_item = self.source_table.item(row, 1)
        if name_item is None:
            return
        source_name = name_item.text()

        # 搜索结果模式下：直接用缓存的原分块内容弹窗
        if getattr(self, "_search_results", None):
            r = self._search_results[row]
            dlg = ChunkViewerDialog(
                r.get("source", source_name),
                [{"chunk_index": r.get("chunk_index", 0), "content": r.get("content", "")}],
                parent=self)
            dlg.exec()
            return

        try:
            chunks = VectorStore().get_chunks(source_name)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"读取知识内容失败：{e}")
            return
        dlg = ChunkViewerDialog(source_name, chunks, parent=self)
        dlg.exec()

    def _on_search(self):
        """搜索知识库 — 结果行显示分块索引，双击/点击行弹窗看完整内容"""
        query = self.search_input.text().strip()
        if not query:
            self._refresh()
            return

        results = knowledge.search(query, limit=20)
        self._search_results = results   # 保存原文，供弹窗使用
        self.source_table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.source_table.setItem(i, 0, QTableWidgetItem(str(i)))
            self.source_table.setItem(i, 1, QTableWidgetItem(r.get("source", "")))
            self.source_table.setItem(i, 2, QTableWidgetItem("搜索结果"))
            self.source_table.setItem(i, 3, QTableWidgetItem(str(r.get("chunk_index", ""))))
            self.source_table.setItem(i, 4, QTableWidgetItem(""))

        self.result_label.setText(
            f"搜索「{query}」找到 {len(results)} 条结果（双击行查看完整内容）" if results
            else f"搜索「{query}」未找到结果"
        )

    def _on_add(self):
        """添加知识"""
        dialog = AddKnowledgeDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._refresh()

    def _on_delete(self):
        """删除选中知识源"""
        rows = self.source_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "提示", "请先选中要删除的知识源")
            return

        reply = QMessageBox.question(self, "确认删除",
            "确定要删除选中的知识源吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for row in rows:
                source_id = self.source_table.item(row.row(), 0).text()
                try:
                    knowledge.delete_source(int(source_id))
                except Exception as e:
                    pass
            self._refresh()

    def _on_ai_query(self):
        """AI 查询知识库"""
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "提示", "请输入问题")
            return

        self.answer_area.setPlainText("⏳ AI 正在查询...")

        # 使用 AgentBehavior 的知识库优先检索
        try:
            agent = AgentBehavior()
            result = agent.knowledge_first_search(query, prefer_region="四川")

            if result["source"] == "knowledge":
                answer = f"[知识库] 找到相关结果：\n\n{result['content'][:500]}"
                if result.get("source_detail"):
                    answer += f"\n\n来源: {result['source_detail']}"
            elif result["source"] == "web":
                answer = f"[网络] 联网搜索结果（已缓存到知识库）：\n\n{result['content'][:500]}"
                if result.get("source_detail"):
                    urls = result["source_detail"]
                    if isinstance(urls, list):
                        answer += f"\n\n来源: {', '.join(urls[:3])}"
            else:
                answer = "知识库和网络均未找到相关数据。\n\n建议：\n1. 手动输入相关知识\n2. 上传相关文档\n3. 检查联网搜索设置"

            self.answer_area.setPlainText(answer)
        except Exception as e:
            self.answer_area.setPlainText(f"查询失败: {e}")
