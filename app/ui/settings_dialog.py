"""API 设置对话框 — 让用户填入自己的 API 地址/密钥/模型

预设说明（2026-09 核实）：
  * 智谱 GLM-4.7-Flash 与腾讯混元 Lite 是官方标注的永久免费模型，
    需自行到对应开放平台注册并领取 API Key（注册免费，无需付费）。
  * Ollama 本地完全离线免费，但需先自行安装 Ollama。
  * 其余平台多为新用户赠送额度，用完即止。
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QDialogButtonBox, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt

from app.utils.config import settings
from app.agent.llm_client import LLMClient


# 预设：(API 地址, Key 占位提示, 模型名, 申请地址)
PRESETS = {
    "智谱 GLM-4.7-Flash（永久免费）": (
        "https://open.bigmodel.cn/api/paas/v4",
        "粘贴你的智谱 API Key",
        "glm-4.7-flash",
        "https://open.bigmodel.cn/",
    ),
    "腾讯混元 Lite（永久免费）": (
        "https://api.hunyuan.cloud.tencent.com/v1",
        "粘贴你的腾讯云 API Key",
        "hunyuan-lite",
        "https://cloud.tencent.com/product/hunyuan",
    ),
    "Ollama 本地（离线免费）": (
        "http://localhost:11434/v1",
        "ollama",
        "qwen2.5:7b",
        "https://ollama.com/download",
    ),
    "DeepSeek 官方": (
        "https://api.deepseek.com/v1",
        "粘贴你的 DeepSeek API Key",
        "deepseek-v4-pro",
        "https://platform.deepseek.com/",
    ),
    "硅基流动 SiliconFlow": (
        "https://api.siliconflow.cn/v1",
        "粘贴你的 SiliconFlow API Key",
        "Qwen/Qwen3-8B-Instruct",
        "https://cloud.siliconflow.cn/",
    ),
    "阿里云百炼（通义千问）": (
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "粘贴你的 DashScope API Key",
        "qwen-plus",
        "https://bailian.console.aliyun.com/",
    ),
    "自定义": ("", "", "", ""),
}


class ApiSettingsDialog(QDialog):
    """API 设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 模型设置")
        self.resize(560, 470)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "本平台需要一个 AI 模型接口来驱动智能助手。\n"
            "不做任何设置也能启动，但 AI 对话与自动分析需要配置后才能使用。\n\n"
            "推荐：智谱 GLM-4.7-Flash 或腾讯混元 Lite —— 官方永久免费，\n"
            "注册开放平台账号即可领取 Key，个人使用完全够。"
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "color: #475569; padding: 10px; background: #F1F5F9;"
            "border-left: 3px solid #EA580C; border-radius: 4px;"
        )
        layout.addWidget(info)

        layout.addSpacing(10)

        provider_group = QGroupBox("快速选择")
        p_layout = QFormLayout(provider_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(list(PRESETS.keys()))
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        p_layout.addRow("API 提供商：", self.provider_combo)

        self.apply_hint = QLabel("")
        self.apply_hint.setWordWrap(True)
        self.apply_hint.setOpenExternalLinks(True)
        self.apply_hint.setStyleSheet("color: #64748B; font-size: 12px;")
        p_layout.addRow("", self.apply_hint)

        layout.addWidget(provider_group)
        layout.addSpacing(10)

        form_group = QGroupBox("API 详细配置")
        form = QFormLayout(form_group)

        self.api_base = QLineEdit()
        self.api_base.setPlaceholderText("https://open.bigmodel.cn/api/paas/v4")
        form.addRow("API 地址：", self.api_base)

        key_row = QVBoxLayout()
        self.api_key = QLineEdit()
        self.api_key.setPlaceholderText("粘贴你的 API Key")
        self.api_key.setEchoMode(QLineEdit.Password)
        key_row.addWidget(self.api_key)

        self.api_key_visible = QPushButton("显示密钥")
        self.api_key_visible.setFixedWidth(90)
        self.api_key_visible.clicked.connect(self._toggle_key_visibility)
        key_row.addWidget(self.api_key_visible)
        form.addRow("API Key：", key_row)

        self.model = QLineEdit()
        self.model.setPlaceholderText("glm-4.7-flash / hunyuan-lite / qwen2.5:7b ...")
        form.addRow("模型名称：", self.model)

        layout.addWidget(form_group)
        layout.addSpacing(8)

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        layout.addWidget(self.test_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_settings(self):
        """加载当前配置，并匹配到对应预设"""
        base = settings.LLM_API_BASE or ""

        # 按 API 地址反查预设名
        matched = "自定义"
        for name, (pbase, _k, _m, _u) in PRESETS.items():
            if pbase and base.rstrip("/") == pbase.rstrip("/"):
                matched = name
                break

        idx = self.provider_combo.findText(matched)
        if idx >= 0:
            # 先切下拉框，再覆盖为已保存的真实值（避免被预设占位符冲掉）
            self.provider_combo.setCurrentIndex(idx)

        self.api_base.setText(base)
        self.api_key.setText(settings.LLM_API_KEY or "")
        self.model.setText(settings.LLM_MODEL or "")

        if matched != "自定义":
            self._update_hint(matched)

    def _update_hint(self, provider: str):
        preset = PRESETS.get(provider)
        if preset and preset[3]:
            self.apply_hint.setText(
                f'申请地址：<a href="{preset[3]}">{preset[3]}</a>　'
                "（注册后在控制台创建 API Key）"
            )
        else:
            self.apply_hint.setText("填入任意 OpenAI 兼容接口的地址与密钥即可。")

    def _on_provider_changed(self, provider: str):
        """根据预设填充 API 配置"""
        preset = PRESETS.get(provider)
        if not preset:
            return
        base, key, model, _url = preset

        if provider == "自定义":
            self.apply_hint.setText("填入任意 OpenAI 兼容接口的地址与密钥即可。")
            self.api_base.clear()
            self.model.clear()
            self.api_key.clear()
            self.api_key.setPlaceholderText("粘贴你的 API Key")
            return

        self.api_base.setText(base)
        self.model.setText(model)
        # Key 用占位提示引导，不写入真实字段，避免用户误以为已配置
        self.api_key.setPlaceholderText(key)
        self.api_key.clear()
        self._update_hint(provider)

    def _toggle_key_visibility(self):
        if self.api_key.echoMode() == QLineEdit.Password:
            self.api_key.setEchoMode(QLineEdit.Normal)
            self.api_key_visible.setText("隐藏密钥")
        else:
            self.api_key.setEchoMode(QLineEdit.Password)
            self.api_key_visible.setText("显示密钥")

    def _test_connection(self):
        base = self.api_base.text().strip()
        key = self.api_key.text().strip()
        model = self.model.text().strip()

        if not base:
            QMessageBox.warning(self, "提示", "请先填写 API 地址。")
            return
        if not model:
            QMessageBox.warning(self, "提示", "请先填写模型名称。")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.repaint()

        try:
            client = LLMClient(api_base=base, api_key=key, model=model)
            ok, msg = client.is_available()
        except Exception as e:
            ok, msg = False, f"测试出错：{e}"

        if ok:
            QMessageBox.information(self, "连接测试结果", msg)
        else:
            QMessageBox.warning(
                self, "连接测试结果",
                msg + "\n\n常见原因：\n"
                      "  · API Key 填错或未领取\n"
                      "  · 模型名称拼写不对\n"
                      "  · 网络不通（本地 Ollama 需先启动 Ollama 程序）"
            )

        self.test_btn.setText("测试连接")
        self.test_btn.setEnabled(True)

    def _on_save(self):
        """保存配置"""
        base = self.api_base.text().strip()
        key = self.api_key.text().strip()
        model = self.model.text().strip()

        if base and not model:
            QMessageBox.warning(self, "提示", "填写了 API 地址就必须填模型名称。")
            return

        settings.LLM_API_BASE = base
        settings.LLM_API_KEY = key
        settings.LLM_MODEL = model
        settings.LLM_PROVIDER = "ollama" if "localhost" in base or "127.0.0.1" in base else "custom"
        settings.save()
        self.accept()
