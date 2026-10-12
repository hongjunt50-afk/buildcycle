"""应用配置"""

import os
import json
from pathlib import Path


CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "config.json"


class Settings:
    """全局配置"""

    # 项目根目录
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent

    # 数据库
    DATA_DIR: Path = ROOT_DIR / "data"
    UPLOAD_DIR: Path = ROOT_DIR / "data" / "uploads"
    DB_PATH: str = str(ROOT_DIR / "data" / "buildcycle.db")
    VECTOR_DB_PATH: str = str(ROOT_DIR / "data" / "vectors.db")

    # 应用
    APP_NAME: str = "BuildCycle 建造全周期管控平台"
    APP_VERSION: str = "0.2.0"
    APP_ORG: str = "buildcycle"

    # AI Agent 配置
    # 默认指向智谱 GLM-4.7-Flash（官方永久免费模型）。
    # 未填写 Key 时 AI 功能不可用，但软件可正常启动与使用全部业务功能；
    # 用户可在「设置 → AI 模型设置」里换成腾讯混元 / Ollama 本地 / 自己的 API。
    LLM_PROVIDER: str = "custom"
    LLM_API_BASE: str = "https://open.bigmodel.cn/api/paas/v4"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "glm-4.7-flash"

    # 知识库
    KB_CHUNK_SIZE: int = 800
    KB_EMBED_DIM: int = 384

    def load(self):
        """从 config.json 加载用户配置"""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if hasattr(self, k.upper()):
                        setattr(self, k.upper(), v)
            except Exception:
                pass

    def save(self):
        """保存用户配置到 config.json"""
        data = {
            "llm_provider": self.LLM_PROVIDER,
            "llm_api_base": self.LLM_API_BASE,
            "llm_api_key": self.LLM_API_KEY,
            "llm_model": self.LLM_MODEL,
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


settings = Settings()
settings.load()
