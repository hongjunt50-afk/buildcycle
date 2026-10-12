"""数据库连接管理"""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.utils.config import settings


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    """SQLite 数据库连接管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self._enable_wal()
        self.SessionLocal = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )

    def _enable_wal(self):
        """启用 WAL 模式提升并发性能"""

        @event.listens_for(self.engine, "connect")
        def set_wal(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    def create_tables(self):
        """创建所有表"""
        from app.database.models import Base  # noqa
        Base.metadata.create_all(bind=self.engine)

    def init_db(self):
        """初始化数据库（建表 + 默认数据）"""
        self.create_tables()
        # 后续可添加默认数据插入
