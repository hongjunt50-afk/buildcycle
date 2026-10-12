# BuildCycle 建造全周期管控平台

**BuildCycle**（建造全周期）—— 面向中小建筑施工企业的开源轻量化项目管理系统。

将工程项目「需求策划 → 招投标 → 施工实施 → 竣工结算与维保」四阶段工作流固化为数字化流程，搭配 AI Agent 辅助做合同风险识别、资料合规校验与智能问答。全部本地运行，数据不出本机。

## 快速开始（给没有编程经验的用户）

**第一次**：双击 `一键安装.bat`，等它自动装完（约 3–10 分钟）。
**以后**：双击桌面图标，或双击 `启动.bat`。

详细图文说明见 [使用说明.md](使用说明.md)。

安装脚本会自动完成：检测 Python → 建独立运行环境 `.venv` → 安装依赖 → 建桌面快捷方式 → 初始化 `data/` 数据库。

## AI 模型配置

软件内置 AI Agent（风险识别、资料校验、智能问答、知识库检索），需要一个大模型接口。
默认指向 **智谱 GLM-4.7-Flash**（官方标注的永久免费模型），你只需去
[bigmodel.cn](https://open.bigmodel.cn) 免费注册、领一个 API Key 填进「设置 → AI 模型设置」即可。

不填也能正常使用全部业务功能，只是 AI 相关按钮不可用。设置里已预置：

| 预设 | 说明 |
|---|---|
| 智谱 GLM-4.7-Flash | 永久免费，需注册领 Key |
| 腾讯混元 Lite | 永久免费，需注册领 Key |
| Ollama 本地 | 完全离线免费，需先自行安装 Ollama |
| DeepSeek / 硅基流动 / 阿里云百炼 | 新用户赠送额度 |
| 自定义 | 任意 OpenAI 兼容接口 |

> 关于"能不能直接对接网页版 DeepSeek"：不能。chat.deepseek.com 没有公开 API，
> 第三方 `deepseek-free-api` 之类的项目是靠浏览器 userToken 逆向中转，
> 违反服务条款且有封号风险，因此本软件不采用。要免费用 DeepSeek，走上面的智谱/混元预设。

## 技术栈

- **GUI**：PySide6（Qt for Python）
- **后端**：Python 原生服务（Agent/MCP/向量库）
- **数据库**：SQLite（业务数据） + sqlite-vec（向量库）
- **运行**：全部本地运行；仅 AI 问答与联网检索需要外网

## 目录说明

```
buildcycle/
├── 一键安装.bat              # 首次安装（双击）
├── 启动.bat                  # 日常启动（双击）
├── install_helper.py         # 安装助手：建快捷方式 + 初始化数据
├── 使用说明.md               # 给非技术用户的说明
├── main.py                   # 程序入口（--init-only 仅初始化不启界面）
├── requirements.txt          # 核心依赖
├── requirements-optional.txt # 可选增强（失败不影响使用）
├── data/                     # 运行数据（数据库/向量库/上传文件）
└── app/                      # 源代码
```

数据全部存在 `data/` 目录里，**备份就复制这个文件夹**。

## 项目结构

```
buildcycle/
├── main.py                    # 入口
├── requirements.txt           # 依赖
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── main_window.py         # 主窗口
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py      # SQLite连接管理
│   │   ├── models.py          # SQLAlchemy模型
│   │   └── migrations.py      # 建库建表
│   ├── modules/
│   │   ├── requirement_planning/  # 需求与策划
│   │   ├── bidding/               # 招投标前期
│   │   ├── construction/          # 施工实施
│   │   └── settlement_warranty/   # 竣工结算与维保
│   ├── agent/
│   │   ├── risk_analyzer.py       # 合同风险识别
│   │   ├── doc_validator.py       # 资料合规校验
│   │   └── chatbot.py             # 智能问答
│   ├── knowledge/
│   │   ├── vector_store.py        # 向量库
│   │   └── knowledge_source.py    # 知识源管理
│   ├── ui/
│   │   ├── dashboard.py           # 仪表盘
│   │   ├── requirement_view.py
│   │   ├── bidding_view.py
│   │   ├── construction_view.py
│   │   ├── settlement_view.py
│   │   └── common/
│   │       ├── table_widget.py
│   │       └── dialog.py
│   └── utils/
│       ├── config.py
│       └── helpers.py
├── resources/
│   └── styles/
│       └── main.qss
└── build/
    └── build_exe.py
```
## 开源许可

本项目基于 [MIT License](LICENSE) 开源。
