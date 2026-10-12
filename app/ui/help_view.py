"""使用说明 — 前端操作指南和工作流使用说明"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QFrame, QSplitter,
    QMessageBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.agent.llm_client import LLMClient
from app.database.connection import DatabaseManager
from app.database.models import *
from sqlalchemy import inspect


class HealthCheckWidget(QFrame):
    """健康检查组件"""

    def __init__(self, title: str, status: str = "待检测", detail: str = ""):
        super().__init__()
        self.setObjectName("healthCheck")

        color = {
            "✅ 正常": "#16A34A",
            "❌ 异常": "#DC2626",
            "⚠️ 警告": "#EA580C",
            "待检测": "#94A3B8",
        }.get(status, "#94A3B8")

        self.setStyleSheet(f"""
            #healthCheck {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
                border-left: 4px solid {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1E293B;")
        header.addWidget(title_label)

        self.status_label = QLabel(status)
        self.status_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: 500;")
        header.addWidget(self.status_label)
        header.addStretch()
        layout.addLayout(header)

        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet("font-size: 11px; color: #64748B;")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

    def update_status(self, status: str, detail: str = ""):
        color = {
            "✅ 正常": "#16A34A",
            "❌ 异常": "#DC2626",
            "⚠️ 警告": "#EA580C",
        }.get(status, "#94A3B8")
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"font-size: 12px; color: {color}; font-weight: 500;")
        self.detail_label.setText(detail)

        self.setStyleSheet(f"""
            #healthCheck {{
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
                border-left: 4px solid {color};
            }}
        """)


class HelpView(QWidget):
    """使用说明页面"""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题区
        header = QHBoxLayout()
        title = QLabel("📖 使用说明")
        title.setProperty("heading", "true")
        header.addWidget(title)
        header.addStretch()

        btn_test = QPushButton("🔍 运行全部检测")
        btn_test.clicked.connect(self._run_all_checks)
        btn_test.setStyleSheet("""
            QPushButton {
                background-color: #16A34A;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #15803D; }
        """)
        header.addWidget(btn_test)

        layout.addLayout(header)

        # 分割：左侧目录 + 右侧内容
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：目录树 ──
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_label = QLabel("目录")
        left_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #475569; padding: 4px 0;")
        left_layout.addWidget(left_label)

        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderHidden(True)
        self.toc_tree.setMinimumWidth(220)
        self.toc_tree.setMaximumWidth(280)
        self.toc_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                background-color: #FFFFFF;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #EFF6FF;
                color: #1E293B;
            }
            QTreeWidget::item:hover {
                background-color: #F8FAFC;
            }
        """)
        self.toc_tree.itemClicked.connect(self._on_toc_clicked)
        left_layout.addWidget(self.toc_tree)

        splitter.addWidget(left_widget)

        # ── 右侧：内容区（Tab切换：使用说明 + 健康检查） ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # 内容标签页
        from PySide6.QtWidgets import QTabWidget as QTabWidget2
        self.content_tabs = QTabWidget2()

        # Tab 1: 使用说明
        self.help_content = QTextEdit()
        self.help_content.setReadOnly(True)
        self.help_content.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                background-color: #FFFFFF;
                padding: 16px;
                font-size: 14px;
                line-height: 1.8;
                color: #334155;
            }
        """)
        self.content_tabs.addTab(self.help_content, "📖 使用说明")

        # Tab 2: 健康检查
        check_widget = QWidget()
        check_layout = QVBoxLayout(check_widget)
        check_layout.setSpacing(12)

        check_title = QLabel("系统健康检查")
        check_title.setProperty("heading", "true")
        check_layout.addWidget(check_title)

        check_desc = QLabel("检测所有模块是否正常运行，点击「运行全部检测」按钮开始。")
        check_desc.setProperty("subheading", "true")
        check_layout.addWidget(check_desc)

        # 检测状态网格
        self.check_grid = QGridLayout()
        self.check_grid.setSpacing(8)

        self.checks = {}
        check_items = [
            ("数据库", "待检测", "点击检测"),
            ("AI 模型", "待检测", "点击检测"),
            ("知识库", "待检测", "点击检测"),
            ("CPM 引擎", "待检测", "点击检测"),
            ("工作流引擎", "待检测", "点击检测"),
            ("EVM 引擎", "待检测", "点击检测"),
            ("资源平衡", "待检测", "点击检测"),
            ("Source Matrix", "待检测", "点击检测"),
            ("蒙特卡洛", "待检测", "点击检测"),
            ("P2P 同步", "待检测", "点击检测"),
        ]

        for i, (name, status, detail) in enumerate(check_items):
            card = HealthCheckWidget(name, status, detail)
            self.checks[name] = card
            self.check_grid.addWidget(card, i // 2, i % 2)

        check_layout.addLayout(self.check_grid)
        check_layout.addStretch()

        self.content_tabs.addTab(check_widget, "🔍 健康检查")

        right_layout.addWidget(self.content_tabs)

        splitter.addWidget(right_widget)
        splitter.setSizes([250, 700])

        layout.addWidget(splitter)

        # 初始化目录和内容
        self._init_toc()
        self._show_content("overview")

    def _init_toc(self):
        """初始化目录树"""
        sections = [
            ("📖 平台概述", "overview", [
                ("系统架构", "architecture"),
                ("快速启动", "quickstart"),
            ]),
            ("📊 仪表盘", "dashboard", []),
            ("📋 需求与策划", "requirement", [
                ("新增需求", "req_add"),
                ("可行性评估", "req_feasibility"),
            ]),
            ("📑 招投标前期", "bidding", [
                ("项目尽调", "bid_diligence"),
                ("合同管理", "bid_contract"),
            ]),
            ("📋 工程量清单", "boq", [
                ("章节管理", "boq_section"),
                ("条目编辑", "boq_item"),
                ("导出Excel", "boq_export"),
            ]),
            ("🏗️ 施工实施", "construction", [
                ("进度计划 + CPM", "con_cpm"),
                ("质量三检", "con_quality"),
                ("安全管理", "con_safety"),
                ("变更签证", "con_change"),
                ("施工资料", "con_doc"),
            ]),
            ("📅 进度计划", "cpm", [
                ("CPM 计算", "cpm_calc"),
                ("Gantt 图", "cpm_gantt"),
                ("资源平衡", "cpm_level"),
            ]),
            ("✅ 竣工结算与维保", "settlement", [
                ("验收整改", "set_issue"),
                ("结算对账", "set_account"),
                ("质保报修", "set_warranty"),
            ]),
            ("⚙️ 工作流", "workflow", [
                ("工作流概念", "wf_concept"),
                ("变更签证审批流", "wf_change"),
                ("质量整改闭环", "wf_quality"),
            ]),
            ("📚 知识库", "knowledge", [
                ("上传文件", "kb_upload"),
                ("手动输入", "kb_manual"),
                ("AI 问答", "kb_query"),
            ]),
            ("💬 AI 助手", "ai_chat", [
                ("打开助手", "ai_open"),
                ("场景示例", "ai_examples"),
            ]),
        ]

        for section_name, section_id, children in sections:
            section_item = QTreeWidgetItem([section_name])
            section_item.setData(0, Qt.UserRole, section_id)
            section_item.setExpanded(True)

            font = section_item.font(0)
            font.setBold(True)
            section_item.setFont(0, font)

            self.toc_tree.addTopLevelItem(section_item)

            for child_name, child_id in children:
                child_item = QTreeWidgetItem([child_name])
                child_item.setData(0, Qt.UserRole, child_id)
                section_item.addChild(child_item)

    def _on_toc_clicked(self, item, column):
        """点击目录项"""
        section_id = item.data(0, Qt.UserRole)
        if section_id:
            self._show_content(section_id)

    def _show_content(self, section_id: str):
        """显示对应内容"""
        content = self._get_content(section_id)
        self.help_content.setHtml(content)

    def _get_content(self, section_id: str) -> str:
        """获取HTML内容"""
        contents = {
            "overview": f"""
<h2>📖 BuildCycle 建造全周期管控平台</h2>
<p>版本：{__import__('app.utils.config', fromlist=['settings']).settings.APP_VERSION}</p>
<hr>
<h3>系统架构</h3>
<p>平台采用 <b>PySide6 + SQLite + sqlite-vec</b> 技术栈，全部本地运行，无需联网。</p>
<ul>
<li><b>GUI</b>：PySide6（Qt for Python）桌面应用</li>
<li><b>数据库</b>：SQLite（业务数据）+ sqlite-vec（向量知识库）</li>
<li><b>AI</b>：Ollama 本地免费 API（默认）/ 可自定义 API</li>
<li><b>部署</b>：双击 exe 即用，零配置</li>
</ul>
<h3>九大功能模块</h3>
<ol>
<li>📊 <b>仪表盘</b> — 项目全局概览</li>
<li>📋 <b>需求与策划</b> — 业主需求录入、可行性评估</li>
<li>📑 <b>招投标前期</b> — 项目尽调、合同管理</li>
<li>📋 <b>工程量清单</b> — BOQ 章节+条目+自动计算+导出</li>
<li>🏗️ <b>施工实施</b> — 进度/质量/安全/变更/资料</li>
<li>📅 <b>进度计划</b> — CPM 计算 + Gantt 图 + 资源平衡</li>
<li>✅ <b>竣工结算与维保</b> — 验收/结算/报修/质保金</li>
<li>⚙️ <b>工作流</b> — 自动化工作流引擎</li>
<li>📚 <b>知识库</b> — 文件上传/手动输入/AI 问答</li>
</ol>
""",
            "architecture": """
<h2>系统架构</h2>
<pre>
buildcycle/
├── app/
│   ├── agent/          AI Agent（行为准则/二次验算/联网搜索）
│   ├── database/       23张业务表
│   ├── knowledge/      知识库（向量检索/文件上传）
│   ├── modules/        业务引擎（CPM/工作流/EVM/资源平衡/...）
│   └── ui/             9个页面 + 浮动AI聊天窗口
├── data/               本地数据库文件
├── 启动.bat            双击启动
└── build/              打包脚本
</pre>
""",
            "quickstart": """
<h2>快速启动</h2>
<ol>
<li>双击 <b>启动.bat</b> 或运行 <code>python main.py</code></li>
<li>系统自动创建 23 张数据库表</li>
<li>默认显示 <b>仪表盘</b> 页签</li>
<li>按 <b>Ctrl+Space</b> 打开 AI 助手</li>
<li>前往 <b>设置 → AI 模型设置</b> 配置 API</li>
</ol>
<p><b>首次使用建议：</b></p>
<ol>
<li>先在「需求与策划」录入一个项目</li>
<li>切换到「工程量清单」添加清单章节和条目</li>
<li>在「知识库」上传一些参考资料</li>
<li>试试 AI 助手提问</li>
</ol>
""",
            "dashboard": """
<h2>📊 仪表盘</h2>
<p>项目全局概览，一键掌握四阶段管控状态。</p>
<h3>功能</h3>
<ul>
<li><b>统计卡片</b>：四个阶段的关键数据（需求数、合同数、在建项目、待结算）</li>
<li><b>最近活动</b>：最新操作记录列表</li>
</ul>
""",
            "requirement": """
<h2>📋 需求与策划</h2>
<p>管理业主需求、可行性评估和项目策划书。</p>
<h3>操作步骤</h3>
<ol>
<li>点击「新增需求」填写项目名称、业主、需求描述</li>
<li>保存后出现在列表中，状态为「草稿」</li>
<li>双击条目可编辑</li>
<li>可进行可行性评估和生成策划书</li>
</ol>
""",
            "req_add": """
<h3>新增需求</h3>
<ol>
<li>点击「＋ 新增需求」按钮</li>
<li>填写项目名称（必填）</li>
<li>填写业主名称</li>
<li>描述需求内容、功能需求、交付标准</li>
<li>设置预算上限</li>
<li>点击确定保存</li>
</ol>
""",
            "req_feasibility": """
<h3>可行性评估</h3>
<p>在需求列表中选中一条需求，可进行可行性评估：</p>
<ul>
<li>录入用地条件、规划指标、市政配套</li>
<li>AI 自动识别风险点并打标签</li>
<li>生成可行性评估报告</li>
</ul>
""",
            "bidding": """
<h2>📑 招投标前期</h2>
<p>项目尽调、合同管理、标书与报价。</p>
<h3>子标签页</h3>
<ul>
<li><b>项目尽调台账</b>：记录业主资信、资金来源、风险备注</li>
<li><b>合同管理</b>：合同归档、AI 风险标签识别</li>
</ul>
""",
            "bid_diligence": """
<h3>项目尽调</h3>
<ol>
<li>切换到「项目尽调台账」子标签</li>
<li>点击「新增尽调」按钮</li>
<li>填写项目名称、业主名称、资金来源、风险备注</li>
<li>AI 会联网查询业主资信信息（四川优先）</li>
</ol>
""",
            "bid_contract": """
<h3>合同管理</h3>
<ol>
<li>切换到「合同管理」子标签</li>
<li>录入合同信息（编号、类型、内容）</li>
<li>AI 自动分析风险条款并打标签</li>
<li>风险类型包括：霸王条款、付款风险、工期风险等</li>
</ol>
""",
            "boq": """
<h2>📋 工程量清单 (BOQ)</h2>
<p>完整的工程量清单管理，支持章节树+条目编辑+自动计算+导出Excel。</p>
<h3>功能</h3>
<ul>
<li><b>章节管理</b>：多级章节树，支持编号</li>
<li><b>条目编辑</b>：编号、名称、单位、数量、单价、自动计算合价</li>
<li><b>自动汇总</b>：章节小计 + 总计</li>
<li><b>导出 Excel</b>：完整清单导出</li>
</ul>
""",
            "boq_section": """
<h3>章节管理</h3>
<ol>
<li>先在上方选择项目</li>
<li>点击「新增章节」按钮</li>
<li>填写章节编号（如 01.01）和名称</li>
<li>在左侧树中选中章节，右侧显示该章节下的清单项</li>
</ol>
""",
            "boq_item": """
<h3>条目编辑</h3>
<ol>
<li>在左侧选中一个章节</li>
<li>点击「新增清单项」</li>
<li>填写编号、名称、选择单位、输入数量和单价</li>
<li>合价自动计算（数量×单价）</li>
<li>双击已有条目可编辑</li>
</ol>
""",
            "boq_export": """
<h3>导出 Excel</h3>
<ol>
<li>选择项目</li>
<li>点击「导出 Excel」按钮</li>
<li>选择保存位置</li>
<li>生成的 Excel 包含所有章节和条目，含小计和总计</li>
</ol>
""",
            "construction": """
<h2>🏗️ 施工实施</h2>
<p>施工阶段的核心管理模块，包含5个子标签。</p>
<h3>子标签页</h3>
<ul>
<li>📅 <b>进度计划</b> — 任务列表和进度跟踪</li>
<li>🔍 <b>质量三检</b> — 自检/互检/交接检</li>
<li>⚠️ <b>安全管理</b> — 隐患整改闭环</li>
<li>📝 <b>变更签证</b> — 变更发起→审批→归档</li>
<li>📄 <b>施工资料</b> — 同步录入+流向数据校验</li>
</ul>
""",
            "con_cpm": """
<h3>进度计划</h3>
<ol>
<li>在施工实施页签中切换到「进度计划」子标签</li>
<li>查看任务列表</li>
<li>更详细的CPM分析请切换到「进度计划」页签</li>
</ol>
""",
            "con_quality": """
<h3>质量三检</h3>
<ol>
<li>切换到「质量三检」子标签</li>
<li>记录自检/互检/交接检结果</li>
<li>不合格项自动进入整改流程</li>
</ol>
""",
            "con_safety": """
<h3>安全管理</h3>
<ol>
<li>切换到「安全管理」子标签</li>
<li>记录隐患项和等级（一般/严重/危急）</li>
<li>指定整改要求和责任人</li>
<li>整改完成后关闭闭环</li>
</ol>
""",
            "con_change": """
<h3>变更签证</h3>
<ol>
<li>切换到「变更签证」子标签</li>
<li>发起变更：填写描述、原因、金额</li>
<li>AI 自动初审 + 金额二次验算</li>
<li>联网查询同类市场价格</li>
<li>人工复审确认后归档</li>
</ol>
""",
            "con_doc": """
<h3>施工资料</h3>
<ol>
<li>切换到「施工资料」子标签</li>
<li>录入施工日志、技术交底、隐蔽验收等</li>
<li>系统自动进行流向数据校验：</li>
<ul>
<li>施工日志日期不得早于技术交底</li>
<li>隐蔽验收必须有关联工序验收</li>
<li>变更签证必须有关联变更令编号</li>
</ul>
<li>校验失败时阻止提交并给出具体错误</li>
</ol>
""",
            "cpm": """
<h2>📅 进度计划 (CPM + Gantt)</h2>
<p>关键路径法调度引擎，支持四种依赖类型，自动计算总工期和关键路径。</p>
<h3>功能</h3>
<ul>
<li><b>CPM 计算</b>：ES/EF/LS/LF/浮动/关键路径</li>
<li><b>Gantt 图</b>：可视化任务条，关键路径橙色高亮</li>
<li><b>资源平衡</b>：检测超载，自动后移非关键任务</li>
<li><b>二次验算</b>：每个计算步骤自动验算</li>
</ul>
""",
            "cpm_calc": """
<h3>CPM 计算</h3>
<ol>
<li>点击「新增任务」添加任务名称和工期</li>
<li>选中两个任务，点击「添加依赖」选择依赖类型</li>
<li>依赖类型：FS(完成-开始)/SS(开始-开始)/FF(完成-完成)/SF(开始-完成)</li>
<li>点击「计算 CPM」自动计算关键路径</li>
<li>关键路径任务橙色高亮显示</li>
</ol>
""",
            "cpm_gantt": """
<h3>Gantt 图</h3>
<p>CPM 计算完成后，Gantt 图自动更新：</p>
<ul>
<li><b>橙色条</b>：关键路径任务</li>
<li><b>灰色条</b>：非关键路径任务</li>
<li><b>绿色填充</b>：任务完成进度</li>
<li><b>虚线区域</b>：浮动时间</li>
</ul>
""",
            "cpm_level": """
<h3>资源平衡</h3>
<ol>
<li>先完成 CPM 计算</li>
<li>点击「资源平衡」按钮</li>
<li>系统自动检测资源超载</li>
<li>非关键任务自动后移</li>
<li>弹出平衡结果报告</li>
</ol>
""",
            "settlement": """
<h2>✅ 竣工结算与维保</h2>
<p>包含验收整改、结算对账、质保报修、质保金跟踪。</p>
<h3>子标签页</h3>
<ul>
<li>🔧 <b>验收整改</b> — 问题闭环管理（PUNCH模式）</li>
<li>💰 <b>结算对账</b> — 合同金额、变更金额、结算金额</li>
<li>🔧 <b>质保报修</b> — 报修工单全流程</li>
<li>🏦 <b>质保金跟踪</b> — 到期提醒、退还跟踪</li>
</ul>
""",
            "set_issue": """
<h3>验收整改</h3>
<ol>
<li>切换到「验收整改」子标签</li>
<li>记录验收问题（描述、责任人、严重程度）</li>
<li>整改完成后标记为关闭</li>
<li>支持上传整改前后照片</li>
</ol>
""",
            "set_account": """
<h3>结算对账</h3>
<ol>
<li>切换到「结算对账」子标签</li>
<li>录入合同金额、变更金额</li>
<li>填写结算金额和审计金额</li>
<li>跟踪结算状态</li>
</ol>
""",
            "set_warranty": """
<h3>质保报修</h3>
<ol>
<li>切换到「质保报修」子标签</li>
<li>记录报修信息和维修人</li>
<li>维修完成后填写结果</li>
<li>质保金跟踪：记录到期日、退还金额</li>
</ol>
""",
            "workflow": """
<h2>⚙️ 工作流自动化</h2>
<p>可配置的自动化工作流引擎，支持自动步骤和人工步骤混合编排。</p>
<h3>工作流概念</h3>
<p>每个工作流由多个步骤组成，每个步骤可以是：</p>
<ul>
<li><b>🤖 自动步骤</b>：AI 自动执行（如初审、计算、联网查询）</li>
<li><b>👤 人工步骤</b>：需要人工判断和操作</li>
</ul>
<h3>已内置的工作流</h3>
<ul>
<li><b>变更签证审批流</b>：5步（发起→AI初审→联网查询→复审→归档）</li>
<li><b>质量整改闭环</b>：6步（登记→AI分类→派发→整改→AI复查→关闭）</li>
</ul>
""",
            "wf_concept": """
<h3>工作流概念</h3>
<p>工作流引擎参考了 EvoFlow 的六阶段方法论：</p>
<ol>
<li><b>发现</b>：当前怎么做</li>
<li><b>分析</b>：哪些可自动化</li>
<li><b>设计</b>：目标工作流</li>
<li><b>构建</b>：实现自动化</li>
<li><b>运行</b>：上线使用</li>
<li><b>支持</b>：持续改进</li>
</ol>
<p>系统中的每个业务模块都是一个可配置的工作流。</p>
""",
            "wf_change": """
<h3>变更签证审批流</h3>
<p><b>流程</b>：发起 → AI初审 → 联网市场价格查询 → 复审汇总 → 确认归档</p>
<ol>
<li><b>发起</b>（人工）：提交变更申请</li>
<li><b>AI初审</b>（自动）：检查描述完整性、金额计算+二次验算</li>
<li><b>联网查询</b>（自动）：查询四川地区同类变更市场价格</li>
<li><b>复审</b>（人工）：审核AI结果和联网数据</li>
<li><b>归档</b>（人工）：确认后归档</li>
</ol>
""",
            "wf_quality": """
<h3>质量整改闭环</h3>
<p><b>流程</b>：问题登记 → AI分类 → 整改派发 → 整改完成 → AI复查 → 关闭归档</p>
<ol>
<li><b>登记</b>（人工）：记录质量问题</li>
<li><b>AI分类</b>（自动）：自动分类严重程度（一般/严重/危急）</li>
<li><b>派发</b>（自动）：AI自动派发到对应责任人</li>
<li><b>整改</b>（人工）：完成整改</li>
<li><b>AI复查</b>（自动）：检查整改结果是否满足要求</li>
<li><b>关闭</b>（人工）：确认后关闭</li>
</ol>
""",
            "knowledge": """
<h2>📚 知识库管理</h2>
<p>上传文件、手动输入知识、联网搜索结果自动缓存。</p>
<h3>功能</h3>
<ul>
<li><b>上传文件</b>：PDF/Word/Excel/TXT/MD/图片</li>
<li><b>手动输入</b>：直接粘贴文本内容</li>
<li><b>AI 问答</b>：先查知识库，未命中联网搜索（四川优先）</li>
<li><b>搜索</b>：关键词搜索知识库内容</li>
<li><b>预览</b>：选中知识源查看内容</li>
</ul>
""",
            "kb_upload": """
<h3>上传文件</h3>
<ol>
<li>点击「添加知识」→ 切换到「上传文件」标签</li>
<li>点击「选择文件」选择本地文件</li>
<li>支持格式：PDF、Word(.docx)、Excel(.xlsx)、TXT、MD、图片</li>
<li>点击「上传并添加到知识库」</li>
<li>系统自动解析内容并向量化存储</li>
</ol>
""",
            "kb_manual": """
<h3>手动输入</h3>
<ol>
<li>点击「添加知识」→ 切换到「手动输入」标签</li>
<li>输入知识名称（如：GB50300-2013）</li>
<li>粘贴知识内容</li>
<li>点击「保存到知识库」</li>
</ol>
""",
            "kb_query": """
<h3>AI 问答</h3>
<ol>
<li>在右侧「向知识库提问」输入框中输入问题</li>
<li>点击「AI 查询」按钮</li>
<li>AI 优先检索本地知识库</li>
<li>未命中时自动联网搜索（四川优先）</li>
<li>结果自动缓存到知识库</li>
</ol>
""",
            "ai_chat": """
<h2>💬 AI 助手（浮动窗口）</h2>
<p>悬浮于所有页面之上的 AI 聊天窗口，独立操作，不影响页面交互。</p>
<h3>打开方式</h3>
<ul>
<li>快捷键：<b>Ctrl+Space</b></li>
<li>菜单：<b>设置 → 💬 AI 助手</b></li>
</ul>
""",
            "ai_open": """
<h3>打开助手</h3>
<ol>
<li>按快捷键 <b>Ctrl+Space</b> 或通过菜单打开</li>
<li>窗口出现在屏幕右下角</li>
<li>拖拽标题栏可移动位置</li>
<li>操作页面不影响聊天窗口</li>
<li>点击「─」最小化，点击「✕」关闭（隐藏而非销毁）</li>
</ol>
""",
            "ai_examples": """
<h3>场景示例</h3>
<p><b>1. 查询施工规范</b></p>
<blockquote>问："GB50300-2013 对隐蔽验收有什么要求？"</blockquote>
<p>→ 先查知识库 → 未命中联网搜索 → 自动缓存结果</p>

<p><b>2. 上传合同分析风险</b></p>
<blockquote>点击📎上传合同文件 → AI自动解析 → 分析风险条款</blockquote>

<p><b>3. 查询材料价格</b></p>
<blockquote>问："四川地区C30混凝土最新信息价"</blockquote>
<p>→ 联网搜索（四川优先）→ 返回结果 → 缓存到知识库</p>

<p><b>4. 主动提醒</b></p>
<p>AI 每30秒自动检查：</p>
<ul>
<li>有需求但没有合同 → 提醒上传</li>
<li>有变更签证但没有施工资料 → 提醒上传</li>
<li>有未整改的验收问题 → 提醒处理</li>
</ul>
""",
        }

        return contents.get(section_id, "<h2>内容加载中...</h2>")

    # ── 健康检查 ──

    def _run_all_checks(self):
        """运行全部检测"""
        self.checks["数据库"].update_status("⏳ 检测中...", "")
        self.checks["AI 模型"].update_status("⏳ 检测中...", "")
        self.checks["知识库"].update_status("⏳ 检测中...", "")
        self.checks["CPM 引擎"].update_status("⏳ 检测中...", "")

        QTimer.singleShot(100, self._check_database)

    def _check_database(self):
        """检测数据库"""
        try:
            inspector = inspect(self.db.engine)
            tables = inspector.get_table_names()
            self.checks["数据库"].update_status(
                "✅ 正常",
                f"{len(tables)} 张表: {', '.join(tables[:5])}..."
            )
        except Exception as e:
            self.checks["数据库"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_ai)

    def _check_ai(self):
        """检测 AI 模型"""
        try:
            from app.utils.config import settings
            client = LLMClient()
            available, msg = client.is_available()
            if available:
                self.checks["AI 模型"].update_status(
                    "✅ 正常",
                    f"{settings.LLM_MODEL} @ {settings.LLM_API_BASE}"
                )
            else:
                self.checks["AI 模型"].update_status(
                    "⚠️ 警告",
                    f"{msg}。可正常使用，AI增强功能需配置API"
                )
        except Exception as e:
            self.checks["AI 模型"].update_status("⚠️ 警告", f"AI 模型未配置: {e}")

        QTimer.singleShot(100, self._check_knowledge)

    def _check_knowledge(self):
        """检测知识库"""
        try:
            from app.knowledge.vector_store import VectorStore
            vs = VectorStore()
            sources = vs.list_sources()
            self.checks["知识库"].update_status(
                "✅ 正常",
                f"{len(sources)} 个知识源"
            )
        except Exception as e:
            self.checks["知识库"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_cpm)

    def _check_cpm(self):
        """检测 CPM 引擎"""
        try:
            from app.modules.cpm_engine import CPMEngine, CPMTask
            engine = CPMEngine()
            engine.add_task(CPMTask(1, "测试", 5))
            engine.add_task(CPMTask(2, "测试2", 3))
            engine.add_dependency(1, 2, "FS")
            result = engine.calculate_with_verify()
            self.checks["CPM 引擎"].update_status(
                "✅ 正常",
                f"总工期 {result['total_duration']} 天, 验算 {'通过' if result['verify_passed'] else '失败'}"
            )
        except Exception as e:
            self.checks["CPM 引擎"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_workflow)

    def _check_workflow(self):
        """检测工作流引擎"""
        try:
            from app.modules.workflow_engine import workflow
            wf_id = workflow.init_change_order_workflow()
            inst_id = workflow.start_instance("change_order", 1)
            result = workflow.advance(inst_id, "AI", "通过", "测试")
            self.checks["工作流引擎"].update_status(
                "✅ 正常",
                f"工作流 {result['status']}, 当前第{result['current_step_index']+1}步"
            )
        except Exception as e:
            self.checks["工作流引擎"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_evm)

    def _check_evm(self):
        """检测 EVM 引擎"""
        try:
            from app.modules.evm_engine import EVMEngine
            evm = EVMEngine("测试", 100000)
            evm.add_period("1月", 50000, 45000, 48000)
            result = evm.calculate()
            self.checks["EVM 引擎"].update_status(
                "✅ 正常",
                f"SPI={result['performance']['spi']}, CPI={result['performance']['cpi']}"
            )
        except Exception as e:
            self.checks["EVM 引擎"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_leveling)

    def _check_leveling(self):
        """检测资源平衡"""
        try:
            from app.modules.resource_leveling import ResourceLevelingEngine
            eng = ResourceLevelingEngine()
            eng.add_resource("工人", 5)
            eng.add_task(1, "测试", 3, 0, 3, 0, 3, True, "工人", 2)
            result = eng.level()
            self.checks["资源平衡"].update_status("✅ 正常", f"引擎可用")
        except Exception as e:
            self.checks["资源平衡"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_source_matrix)

    def _check_source_matrix(self):
        """检测 Source Matrix"""
        try:
            from app.modules.source_matrix import SourceMatrix
            sm = SourceMatrix()
            sm.init_default_rules()
            result = sm.validate_document("施工日志", {
                "project_name": "测试", "content": "...",
                "related_date": "2026-09-09", "created_by": "施工员"
            })
            self.checks["Source Matrix"].update_status(
                "✅ 正常",
                f"4条预设规则, 校验结果: {'通过' if result['valid'] else '失败'}"
            )
        except Exception as e:
            self.checks["Source Matrix"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_monte_carlo)

    def _check_monte_carlo(self):
        """检测蒙特卡洛"""
        try:
            from app.modules.monte_carlo import MonteCarloEngine, PERTTask
            mc = MonteCarloEngine(iterations=200)
            mc.add_task(PERTTask(1, "测试", 2, 3, 5))
            result = mc.run()
            self.checks["蒙特卡洛"].update_status(
                "✅ 正常",
                f"{result['iterations']}次模拟, 期望{result['statistics']['mean']}天"
            )
        except Exception as e:
            self.checks["蒙特卡洛"].update_status("❌ 异常", str(e))

        QTimer.singleShot(100, self._check_sync)

    def _check_sync(self):
        """检测 P2P 同步"""
        try:
            from app.modules.sync_engine import SyncEngine
            sync = SyncEngine()
            status = sync.get_sync_status()
            self.checks["P2P 同步"].update_status(
                "✅ 正常",
                f"节点 {status['node_id']}, 端口 {status['port']}"
            )
        except Exception as e:
            self.checks["P2P 同步"].update_status("❌ 异常", str(e))

        self.content_tabs.setCurrentIndex(1)
