"""浮动 AI 聊天窗口 — 悬浮于所有页面之上，独立交互"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QFrame, QScrollArea, QWidget, QFileDialog, QMessageBox,
    QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QIcon, QPixmap

from app.agent.agent_core import AgentBehavior
from app.knowledge.knowledge_manager import knowledge
from app.agent.llm_client import LLMClient


class ChatBubble(QFrame):
    """聊天气泡组件 — 悬停显示「复制 / 删除」操作按钮"""

    deleted = Signal(object)   # 气泡被删除时发出（参数 = self）

    def __init__(self, text: str, is_ai: bool = True, timestamp: str = "",
                 memory_id: int = None, session_id: str = "default",
                 deletable: bool = True):
        super().__init__()
        self.setObjectName("chatBubble")
        self.raw_text = text              # 原始文本（复制用，不含富文本）
        self.memory_id = memory_id        # 记忆库里的行 ID（删除用）
        self.session_id = session_id

        bg = "#1E293B" if is_ai else "#EA580C"
        align = Qt.AlignLeft if is_ai else Qt.AlignRight
        margin_left = 48 if is_ai else 12
        margin_right = 12 if is_ai else 48

        self.setStyleSheet(f"""
            #chatBubble {{
                background-color: {bg};
                border-radius: 12px;
                padding: 10px 14px;
                margin: 4px {margin_right}px 4px {margin_left}px;
            }}
            #chatBubble:hover {{
                border: 1px solid #475569;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 标签 + 操作按钮行
        header = QHBoxLayout()
        label = QLabel("🤖 AI" if is_ai else "👤 我")
        label.setStyleSheet(f"color: {'#94A3B8' if is_ai else '#FED7AA'}; font-size: 11px; font-weight: 600;")
        header.addWidget(label)

        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setStyleSheet("color: #64748B; font-size: 10px;")
            header.addWidget(time_label)

        header.addStretch()

        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-size: 11px;
                padding: 1px 5px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #334155; color: #F1F5F9; }
        """
        # 复制按钮：把本条消息原文放进剪贴板
        btn_copy = QPushButton("复制")
        btn_copy.setToolTip("复制这条消息")
        btn_copy.setStyleSheet(btn_style)
        btn_copy.clicked.connect(self._copy_text)
        header.addWidget(btn_copy)

        # 删除按钮：同时删除界面气泡 + 记忆库记录
        if deletable:
            btn_del = QPushButton("删除")
            btn_del.setToolTip("删除这条消息（同时从 AI 记忆中移除）")
            btn_del.setStyleSheet(btn_style)
            btn_del.clicked.connect(self._delete_self)
            header.addWidget(btn_del)

        layout.addLayout(header)

        # 消息内容
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.text_label.setStyleSheet(f"color: {'#F1F5F9' if is_ai else '#FFFFFF'}; font-size: 13px;")
        self.text_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.text_label)

        # 如果是AI主动询问文件，显示上传按钮
        if is_ai and "请上传" in text or "请提交" in text or "缺少" in text:
            btn_upload = QPushButton("📁 上传文件")
            btn_upload.setStyleSheet("""
                QPushButton {
                    background-color: #334155;
                    color: #F1F5F9;
                    border: 1px solid #475569;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    margin-top: 4px;
                }
                QPushButton:hover {
                    background-color: #475569;
                }
            """)
            btn_upload.clicked.connect(self._on_upload)
            layout.addWidget(btn_upload)

        self.setMaximumWidth(480)

    def _copy_text(self):
        """复制原始文本到剪贴板（Markdown 源文，而非渲染后的样子）"""
        QApplication.clipboard().setText(self.raw_text)
        # 轻提示：短暂改按钮文字
        btn = self.sender()
        if btn:
            old = btn.text()
            btn.setText("已复制")
            QTimer.singleShot(1200, lambda: btn.setText(old) if btn else None)

    def _delete_self(self):
        """删除本条消息：界面气泡 + 记忆库 + 知识库同步分块"""
        try:
            from app.knowledge.conversation_memory import memory as conv_memory
            from app.knowledge.vector_store import VectorStore
            if self.memory_id is not None:
                conv_memory.delete_message(self.memory_id, session_id=self.session_id)
                VectorStore().delete_memory_chunks(self.session_id, self.raw_text)
        except Exception:
            pass  # 记忆库删除失败不阻塞界面删除
        self.deleted.emit(self)
        self.deleteLater()

    def _on_upload(self):
        """上传文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "",
            "支持的文件 (*.pdf *.docx *.xlsx *.txt *.md *.jpg *.png);;所有文件 (*)"
        )
        if path:
            result = knowledge.add_file(path)
            if result["status"] == "ok":
                # 发送信号通知父窗口
                parent = self.parent()
                while parent and not hasattr(parent, 'on_file_uploaded'):
                    parent = parent.parent()
                if parent and hasattr(parent, 'on_file_uploaded'):
                    parent.on_file_uploaded(path, result)


class FloatingChatWindow(QDialog):
    """浮动 AI 聊天窗口 — 悬浮于所有页面之上"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 助手")
        self.setObjectName("floatingChat")

        # 窗口标志：无边框、工具窗口、置顶
        self.setWindowFlags(
            Qt.Dialog |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self.resize(420, 560)
        self.setMinimumSize(320, 400)

        # 拖拽相关
        self.dragging = False
        self.drag_start = QPoint()

        # 初始化位置（右下角）
        self._init_position()

        # 消息历史
        self.messages = []
        self._pending_request = False    # 有 LLM 请求在后台跑
        self._thinking_bubble = None     # 「正在思考」占位气泡

        # AI Agent
        self.agent = AgentBehavior()

        # 自检定时器（检查缺少的文件）
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._auto_check)
        self.check_timer.start(30000)  # 每30秒检查一次

        self._setup_ui()
        self._send_welcome()

    def _init_position(self):
        """初始化位置（屏幕右下角）"""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - 440
            y = geometry.bottom() - 600
            self.move(x, y)

    def _setup_ui(self):
        """构建 UI"""
        self.setStyleSheet("""
            #floatingChat {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 标题栏（可拖拽） ──
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet("""
            #titleBar {
                background-color: #1E293B;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                padding: 8px 12px;
            }
        """)
        title_bar.setFixedHeight(40)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)

        icon_label = QLabel("💬")
        icon_label.setStyleSheet("font-size: 16px;")
        title_layout.addWidget(icon_label)

        title_text = QLabel("AI 工程助手")
        title_text.setStyleSheet("color: #F1F5F9; font-size: 14px; font-weight: 600;")
        title_layout.addWidget(title_text)

        title_layout.addStretch()

        # 最小化按钮
        btn_min = QPushButton("─")
        btn_min.setFixedSize(28, 28)
        btn_min.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #334155; color: #F1F5F9; }
        """)
        btn_min.clicked.connect(self.hide)
        title_layout.addWidget(btn_min)

        # 关闭按钮
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #DC2626; color: #FFFFFF; }
        """)
        btn_close.clicked.connect(self.close)
        title_layout.addWidget(btn_close)

        layout.addWidget(title_bar)

        # 使标题栏可拖拽
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move
        title_bar.mouseReleaseEvent = self._title_mouse_release

        # ── 消息区域 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0F172A;
            }
            QScrollBar:vertical {
                background-color: #1E293B;
                width: 6px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(8, 8, 8, 8)
        self.message_layout.setSpacing(4)
        self.message_layout.addStretch()

        scroll.setWidget(self.message_container)
        layout.addWidget(scroll, stretch=1)

        # ── 输入区域 ──
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            background-color: #1E293B;
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            padding: 8px;
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 4, 8, 4)
        input_layout.setSpacing(6)

        # 文件上传按钮
        btn_file = QPushButton("📎")
        btn_file.setFixedSize(36, 36)
        btn_file.setToolTip("上传文件到知识库")
        btn_file.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #94A3B8;
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #475569; color: #F1F5F9; }
        """)
        btn_file.clicked.connect(self._on_upload_file)
        input_layout.addWidget(btn_file)

        # 清空对话按钮：一键删光本次聊天的所有消息（界面+记忆库）
        btn_clear = QPushButton("🧹")
        btn_clear.setFixedSize(36, 36)
        btn_clear.setToolTip("清空当前对话（含 AI 记忆）")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #94A3B8;
                border: none;
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #7F1D1D; color: #F1F5F9; }
        """)
        btn_clear.clicked.connect(self._on_clear_chat)
        input_layout.addWidget(btn_clear)

        # 输入框
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入问题，或描述需要什么资料...")
        self.input_edit.setFixedHeight(36)
        self.input_edit.setStyleSheet("""
            QTextEdit {
                background-color: #0F172A;
                color: #F1F5F9;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #334155;
            }
            QTextEdit:focus {
                border-color: #EA580C;
            }
        """)
        self.input_edit.installEventFilter(self)
        input_layout.addWidget(self.input_edit, stretch=1)

        # 发送按钮
        btn_send = QPushButton("发送")
        btn_send.setFixedSize(56, 36)
        btn_send.setStyleSheet("""
            QPushButton {
                background-color: #EA580C;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #D24E0A; }
            QPushButton:pressed { background-color: #B84308; }
        """)
        btn_send.clicked.connect(self._on_send)
        input_layout.addWidget(btn_send)

        layout.addWidget(input_frame)

    # ── 标题栏拖拽 ──

    def _title_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start = event.globalPos() - self.frameGeometry().topLeft()

    def _title_mouse_move(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.drag_start)

    def _title_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    # ── 消息管理 ──

    def add_message(self, text: str, is_ai: bool = True,
                    memory_id: int = None, deletable: bool = True):
        """添加消息气泡；memory_id 用于删除时同步记忆库"""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")

        bubble = ChatBubble(text, is_ai, ts, memory_id=memory_id,
                            session_id="floating_chat", deletable=deletable)
        bubble.deleted.connect(self._on_bubble_deleted)

        # 插入到 Stretch 之前
        self.message_layout.insertWidget(
            self.message_layout.count() - 1, bubble
        )

        self.messages.append({"text": text, "is_ai": is_ai, "time": ts,
                              "bubble": bubble})

        # 自动滚动到底部
        parent = bubble.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scrollbar = parent.verticalScrollBar()
                if scrollbar:
                    QTimer.singleShot(100, lambda: scrollbar.setValue(scrollbar.maximum()))
                break
            parent = parent.parent()

    def _on_bubble_deleted(self, bubble):
        """气泡删除后：从 self.messages 里同步移除（按引用精确匹配）"""
        for i, m in enumerate(self.messages):
            if m.get("bubble") is bubble:
                del self.messages[i]
                break

    def _send_welcome(self):
        """发送欢迎消息"""
        welcome = (
            "你好！我是 **AI 工程助手** 🤖\n\n"
            "我可以帮你：\n"
            "• 回答工程管理问题（先查知识库，未命中联网搜索）\n"
            "• 检查项目缺少哪些资料，提醒你上传\n"
            "• 分析合同风险、计算工程量\n"
            "• 推进工作流自动化\n\n"
            "你可以直接提问，或上传文件让我学习。"
        )
        self.add_message(welcome, is_ai=True)

        # 主动检查一次
        QTimer.singleShot(2000, self._auto_check)

    def _on_send(self):
        """发送消息 — 网络请求走后台线程，主线程绝不阻塞"""
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        if self._pending_request:
            return  # 上一条还没回来，防重入

        self.input_edit.clear()
        self.add_message(text, is_ai=False)

        # 禁用发送按钮
        self._set_input_enabled(False)
        self._thinking_bubble = self.add_message("⏳ 正在思考...", is_ai=True)

        # 后台线程执行 LLM 请求（原先在主线程跑，30 秒超时窗口内整个平台冻结）
        client = LLMClient()
        self._pending_request = True
        client.chat_with_memory_async(
            text, session_id="floating_chat", temperature=0.5, max_tokens=1000,
            on_done=self._on_llm_reply,
            on_error=self._on_llm_error,
        )

    def _on_llm_reply(self, reply: str):
        """后台线程回来：替换「正在思考」为真实回复（主线程）"""
        self._pending_request = False
        self._set_input_enabled(True)
        if self._thinking_bubble is not None:
            self._thinking_bubble.deleteLater()
            self._thinking_bubble = None
            # 删掉 messages 里对应的"正在思考"占位
            for i, m in enumerate(self.messages):
                if m["text"] == "⏳ 正在思考...":
                    del self.messages[i]
                    break
        self.add_message(reply, is_ai=True)

    def _on_llm_error(self, err: str):
        """后台线程出错：给用户可读的提示（主线程）"""
        self._pending_request = False
        self._set_input_enabled(True)
        if self._thinking_bubble is not None:
            self._thinking_bubble.deleteLater()
            self._thinking_bubble = None
            for i, m in enumerate(self.messages):
                if m["text"] == "⏳ 正在思考...":
                    del self.messages[i]
                    break
        self.add_message(f"❌ AI 服务暂时无法连接（{err[:80]}）。\n"
                         "你可以先使用其他功能，或稍后再试。", is_ai=True)

    def _set_input_enabled(self, enabled: bool):
        """启用/禁用输入"""
        self.input_edit.setEnabled(enabled)

    def _process_query(self, text: str):
        """本地规则路由（不联网，可在主线程跑）"""
        try:
            # 判断查询类型
            if any(kw in text for kw in ["上传", "文件", "资料", "文档"]):
                self._handle_file_request(text)
            elif any(kw in text for kw in ["合同", "风险"]):
                self._handle_contract_risk(text)
            elif any(kw in text for kw in ["计算", "BOQ", "清单", "工程量"]):
                self._handle_boq_query(text)
            else:
                self._handle_general_query(text)
        except Exception as e:
            self.add_message(f"处理出错: {e}", is_ai=True)

    def _handle_general_query(self, text: str):
        """通用查询（带记忆+知识库优先→联网兜底）"""
        try:
            # 使用带记忆的对话（本地规则命中时直接走异步 LLM）
            client = LLMClient()
            self._set_input_enabled(False)
            self._pending_request = True
            self._thinking_bubble = self.add_message("⏳ 正在思考...", is_ai=True)
            client.chat_with_memory_async(
                text, session_id="floating_chat", temperature=0.5, max_tokens=1000,
                on_done=self._on_llm_reply,
                on_error=self._on_llm_error,
            )
        except Exception:
            # 回退到原有逻辑（本地知识库，不联网）
            result = self.agent.knowledge_first_search(text, prefer_region="四川")

            if result["source"] == "knowledge":
                answer = f"📚 **知识库结果**\n\n{result['content'][:600]}"
                if result.get("source_detail"):
                    answer += f"\n\n来源: `{result['source_detail']}`"
            elif result["source"] == "web":
                answer = f"🌐 **联网搜索结果**（已缓存到知识库）\n\n{result['content'][:600]}"
                if result.get("source_detail"):
                    urls = result["source_detail"]
                    if isinstance(urls, list):
                        answer += f"\n\n来源: {', '.join(urls[:3])}"
            else:
                answer = (
                    "❌ **未找到相关信息**\n\n"
                    "建议：\n"
                    "1. 上传相关文件到知识库（点击输入框旁的📎）\n"
                    "2. 换个关键词试试\n"
                    "3. 检查联网搜索设置（菜单栏→设置→AI模型设置）"
                )

            self.add_message(answer, is_ai=True)

    def _handle_file_request(self, text: str):
        """处理文件相关请求"""
        answer = (
            "📁 **文件上传指引**\n\n"
            "请点击输入框左侧的 **📎 按钮** 选择文件：\n\n"
            "支持格式：\n"
            "• PDF 文档（合同、规范、图纸）\n"
            "• Word 文档（施工方案、技术交底）\n"
            "• Excel 表格（工程量清单、报价单）\n"
            "• 图片（现场照片、签字单）\n"
            "• TXT/Markdown 文本\n\n"
            "上传后我会自动解析内容并存入知识库。"
        )
        self.add_message(answer, is_ai=True)

    def _handle_contract_risk(self, text: str):
        """处理合同风险分析"""
        answer = (
            "📋 **合同风险分析**\n\n"
            "请上传合同文件，我会自动分析：\n"
            "• 霸王条款（最终解释权、单方变更等）\n"
            "• 付款风险（无预付款、垫资条款等）\n"
            "• 工期风险（不合理工期、高额违约金）\n"
            "• 责任转移条款\n\n"
            "点击下方 📎 按钮上传合同文件。"
        )
        self.add_message(answer, is_ai=True)

    def _handle_boq_query(self, text: str):
        """处理工程量清单查询"""
        answer = (
            "📊 **工程量清单 (BOQ)**\n\n"
            "工程量清单管理在 **📋 工程量清单** 页签中。\n\n"
            "我可以帮你：\n"
            "• 计算清单项合价（数量×单价）\n"
            "• 汇总章节小计和总计\n"
            "• 导出Excel文件\n"
            "• 关联到项目需求\n\n"
            "请先切换到工程量清单页签，或者上传Excel清单文件让我解析。"
        )
        self.add_message(answer, is_ai=True)

    def _on_clear_chat(self):
        """清空当前对话：删光气泡 + 清记忆库 + 清知识库同步分块"""
        if self._pending_request:
            QMessageBox.information(self, "提示", "AI 还在回复中，请稍后再清空。")
            return
        reply = QMessageBox.question(
            self, "清空对话",
            "确定清空当前对话吗？\n聊天记录和 AI 对这段对话的记忆都会被删除。",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        # 界面气泡
        for i in reversed(range(self.message_layout.count())):
            item = self.message_layout.itemAt(i)
            w = item.widget() if item else None
            if w is not None and isinstance(w, ChatBubble):
                w.deleteLater()
        self.messages.clear()
        # 记忆库 + 知识库
        try:
            from app.knowledge.conversation_memory import memory as conv_memory
            from app.knowledge.vector_store import VectorStore
            conv_memory.clear_session("floating_chat")
            vs = VectorStore()
            vs.conn.execute("DELETE FROM knowledge_embeddings WHERE source LIKE '记忆:floating_chat:%'")
            vs.conn.commit()
        except Exception:
            pass
        self._send_welcome()

    def _remove_last_ai_message(self):
        """移除最后一条AI消息（用于替换"思考中..."）"""
        for i in reversed(range(self.message_layout.count())):
            item = self.message_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, 'text_label') and "⏳" in w.text_label.text():
                    w.deleteLater()
                    break

    def on_file_uploaded(self, path: str, result: dict):
        """文件上传成功回调"""
        name = result.get("name", path.split("/")[-1].split("\\")[-1])
        self.add_message(
            f"✅ 文件已上传并解析: **{name}**\n"
            f"内容已存入知识库，可随时查询。",
            is_ai=True
        )

    def _on_upload_file(self):
        """上传文件按钮"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件上传到知识库", "",
            "支持的文件 (*.pdf *.docx *.xlsx *.txt *.md *.jpg *.png);;所有文件 (*)"
        )
        if path:
            filename = path.replace("\\", "/").split("/")[-1]
            self.add_message(f"正在上传文件: {filename}...", is_ai=False)
            result = knowledge.add_file(path)
            if result["status"] == "ok":
                self.on_file_uploaded(path, result)
            else:
                self.add_message(f"❌ 上传失败: {result.get('message', '未知错误')}", is_ai=True)

    # ── 自动检查（AI主动发现缺少的资料） ──

    def _auto_check(self):
        """自动检查项目是否缺少资料"""
        try:
            from app.database.connection import DatabaseManager
            from app.database.models import (
                ProjectRequirement, Contract, ChangeOrder,
                ConstructionDoc, CompletionIssue
            )

            db = DatabaseManager()
            session = db.get_session()

            messages = []

            # 检查1：有需求但没有合同
            req_count = session.query(ProjectRequirement).count()
            contract_count = session.query(Contract).count()
            if req_count > 0 and contract_count == 0:
                messages.append(
                    f"📋 有 **{req_count} 个需求** 但还没有合同资料。\n"
                    "请上传合同文件，我会自动分析风险条款。"
                )

            # 检查2：有变更签证但没有施工资料
            change_count = session.query(ChangeOrder).count()
            doc_count = session.query(ConstructionDoc).count()
            if change_count > 0 and doc_count == 0:
                messages.append(
                    f"📝 有 **{change_count} 个变更签证** 但还没有施工资料。\n"
                    "请上传施工日志、技术交底等资料。"
                )

            # 检查3：有验收问题但没有整改完成
            open_issues = session.query(CompletionIssue).filter(
                CompletionIssue.status == "open"
            ).count()
            if open_issues > 0:
                messages.append(
                    f"⚠️ 还有 **{open_issues} 个验收问题** 未整改完成。\n"
                    "请切换到「竣工结算与维保」页签处理。"
                )

            # 检查4：知识库为空
            from app.knowledge.vector_store import VectorStore
            vs = VectorStore()
            sources = vs.list_sources()
            if len(sources) == 0:
                messages.append(
                    "📚 **知识库为空**，建议上传一些参考资料：\n"
                    "• 施工规范（GB系列）\n"
                    "• 企业内部标准\n"
                    "• 历史项目资料\n"
                    "点击📎按钮上传文件。"
                )

            session.close()

            if messages:
                for msg in messages:
                    self.add_message(msg, is_ai=True)

        except Exception as e:
            pass  # 自动检查失败时不打扰用户

    def showEvent(self, event):
        """显示时自动检查"""
        super().showEvent(event)
        self._auto_check()

    def closeEvent(self, event):
        """关闭时隐藏而不是销毁"""
        self.hide()
        event.ignore()
