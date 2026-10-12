"""向量库管理 — sqlite-vec"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from app.utils.config import settings


class VectorStore:
    """sqlite-vec 向量库管理"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.VECTOR_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()   # SQLite 连接不能跨线程用，每线程一条
        self._init_schema()

    @property
    def conn(self):
        """线程局部的 SQLite 连接 — 后台线程（异步 LLM 请求）也能安全读写"""
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.db_path)
            self._local.conn = c
        return c

    def _init_schema(self):
        """初始化向量库表结构"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_source (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'manual',
                content TEXT,
                chunk_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.commit()

    def add_text(self, source: str, content: str, embedding: Optional[bytes] = None, source_type: str = "manual"):
        """添加文本到向量库"""
        # 简单分块（按800字分块）
        chunk_size = settings.KB_CHUNK_SIZE
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

        for i, chunk in enumerate(chunks):
            self.conn.execute(
                "INSERT INTO knowledge_embeddings (source, chunk_index, content, embedding) VALUES (?, ?, ?, ?)",
                (source, i, chunk, embedding),
            )

        self.conn.execute(
            "INSERT INTO knowledge_source (name, source_type, content, chunk_count) VALUES (?, ?, ?, ?)",
            (source, source_type, content[:200], len(chunks)),
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 5) -> list:
        """关键词搜索（无向量时用LIKE回退）"""
        cursor = self.conn.execute(
            "SELECT source, chunk_index, content FROM knowledge_embeddings WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        )
        return [
            {"source": row[0], "chunk_index": row[1], "content": row[2]}
            for row in cursor.fetchall()
        ]

    def list_sources(self) -> list:
        """列出所有知识源"""
        cursor = self.conn.execute(
            "SELECT id, name, source_type, chunk_count, created_at FROM knowledge_source ORDER BY id DESC"
        )
        return [
            {"id": row[0], "name": row[1], "source_type": row[2],
             "chunk_count": row[3], "created_at": row[4]}
            for row in cursor.fetchall()
        ]

    def get_chunks(self, source: str) -> list:
        """取某知识源的全部分块（完整内容，不截断），按分块顺序返回"""
        cursor = self.conn.execute(
            "SELECT chunk_index, content FROM knowledge_embeddings "
            "WHERE source = ? ORDER BY chunk_index ASC",
            (source,),
        )
        return [{"chunk_index": row[0], "content": row[1]} for row in cursor.fetchall()]

    def get_chunk(self, source: str, chunk_index: int) -> Optional[str]:
        """取单个分块的完整内容"""
        cursor = self.conn.execute(
            "SELECT content FROM knowledge_embeddings WHERE source = ? AND chunk_index = ?",
            (source, chunk_index),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def delete_memory_chunks(self, session_id: str, content: str) -> int:
        """删除对话记忆同步到知识库的分块（source 前缀 = 记忆:会话:话题）"""
        chunk_size = settings.KB_CHUNK_SIZE
        chunks = list(dict.fromkeys(
            content[i:i + chunk_size] for i in range(0, len(content), chunk_size)
        ))
        if not chunks:
            return 0
        deleted = 0
        for chunk in chunks:
            cur = self.conn.execute(
                "DELETE FROM knowledge_embeddings "
                "WHERE source LIKE ? AND content = ?",
                (f"记忆:{session_id}:%", chunk),
            )
            deleted += cur.rowcount
        self.conn.commit()
        return deleted

    def close(self):
        self.conn.close()
