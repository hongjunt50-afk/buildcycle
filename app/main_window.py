"""主窗口 — 四模块 Tab + 新增功能页签"""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QStatusBar, QMessageBox, QMenuBar, QMenu
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QIcon

from app.utils.config import settings
from app.database.connection import DatabaseManager
from app.ui.settings_dialog import ApiSettingsDialog
from app.ui.floating_chat import FloatingChatWindow


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.db.init_db()

        # 浮动聊天窗口
        self.chat_window = FloatingChatWindow(self)

        self.setWindowTitle(f"{settings.APP_NAME} v{settings.APP_VERSION}")
        self.resize(1400, 900)

        # 窗口/任务栏图标（resources/app.ico 随包发布；缺了也不影响使用）
        icon_path = settings.ROOT_DIR / "resources" / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_menu()
        self._setup_ui()
        self._load_style()

    def _setup_menu(self):
        """构建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")

        chat_action = QAction("💬 AI 助手", self)
        chat_action.setShortcut("Ctrl+Space")
        chat_action.triggered.connect(self._toggle_chat)
        settings_menu.addAction(chat_action)

        settings_menu.addSeparator()

        api_action = QAction("AI 模型设置...", self)
        api_action.triggered.connect(self._open_settings)
        settings_menu.addAction(api_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _open_settings(self):
        """打开 API 设置对话框"""
        dialog = ApiSettingsDialog(self)
        if dialog.exec() == ApiSettingsDialog.Accepted:
            self.status_bar.showMessage("✅ AI 模型设置已保存")

    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            f"{settings.APP_NAME} v{settings.APP_VERSION}\n\n"
            "面向中小建筑施工企业的轻量化项目管理系统\n"
            "技术栈：PySide6 + SQLite + sqlite-vec\n"
            "AI 默认使用 Ollama 本地免费 API\n"
            "全部本地运行，无需联网"
        )

    def _toggle_chat(self):
        """切换 AI 助手窗口显示"""
        if self.chat_window.isVisible():
            self.chat_window.hide()
        else:
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()

    def _setup_ui(self):
        """构建 UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # 页签
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 原有五个模块 Tab
        from app.ui.dashboard import DashboardView
        from app.ui.requirement_view import RequirementView
        from app.ui.bidding_view import BiddingView
        from app.ui.construction_view import ConstructionView
        from app.ui.settlement_view import SettlementView

        self.tabs.addTab(DashboardView(self.db), "📊 仪表盘")
        self.tabs.addTab(RequirementView(self.db), "📋 需求与策划")
        self.tabs.addTab(BiddingView(self.db), "📑 招投标前期")
        self.tabs.addTab(ConstructionView(self.db), "🏗️ 施工实施")
        self.tabs.addTab(SettlementView(self.db), "✅ 竣工结算与维保")

        # P1/P2 新增功能页签
        from app.ui.knowledge_view import KnowledgeView
        from app.ui.workflow_view import WorkflowView
        from app.ui.boq_view import BoqView
        from app.ui.cpm_gantt_view import CpmGanttView

        self.tabs.addTab(KnowledgeView(self.db), "📚 知识库")
        self.tabs.addTab(WorkflowView(self.db), "⚙️ 工作流")
        self.tabs.addTab(BoqView(self.db), "📋 工程量清单")
        self.tabs.addTab(CpmGanttView(self.db), "📅 进度计划")

        # 帮助说明
        from app.ui.help_view import HelpView
        self.tabs.addTab(HelpView(self.db), "📖 使用说明")

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _load_style(self):
        """加载 QSS 样式"""
        style_path = settings.ROOT_DIR / "resources" / "styles" / "main.qss"
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())