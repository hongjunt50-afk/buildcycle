"""对话记忆库 — 存储历史对话内容到知识库"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from app.utils.config import settings


class ConversationMemory:
    """
    对话记忆库
    存储每次对话的内容到向量库，支持按时间/关键词检索
    """

    def __init__(self):
        self.db_path = settings.VECTOR_DB_PATH
        # 本类在模块导入期就被实例化，早于数据库初始化，
        # 因此必须自己确保父目录存在，否则首次运行/清理 data 后会
        # 直接抛 sqlite3.OperationalError: unable to open database file。
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
        """初始化记忆库表"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                topic TEXT,
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_session
            ON conversation_memory(session_id, created_at)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_topic
            ON conversation_memory(topic)
        """)
        self.conn.commit()

    def add_message(self, role: str, content: str, session_id: str = "default", topic: str = "") -> int:
        """
        添加一条对话记录到记忆库
        role: user / assistant / system
        """
        # 自动提取话题（取前20字）
        if not topic:
            topic = content[:20].replace("\n", " ") if len(content) > 20 else content.replace("\n", " ")

        cursor = self.conn.execute(
            "INSERT INTO conversation_memory (session_id, role, content, topic, summary) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, topic, topic[:50])
        )
        self.conn.commit()

        # 同时存入知识库（方便向量检索）
        self._sync_to_knowledge(content, topic, session_id)

        return cursor.lastrowid

    def _sync_to_knowledge(self, content: str, topic: str, session_id: str):
        """同步到知识库，方便向量检索"""
        try:
            from app.knowledge.vector_store import VectorStore
            vs = VectorStore()
            vs.add_text(
                source=f"记忆:{session_id}:{topic}",
                content=content,
                source_type="conversation_memory",
            )
        except Exception:
            pass

    def get_recent(self, limit: int = 20, session_id: str = "default") -> List[Dict]:
        """获取最近的对话记录"""
        cursor = self.conn.execute(
            "SELECT id, role, content, topic, created_at FROM conversation_memory "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        )
        return [
            {"id": row[0], "role": row[1], "content": row[2],
             "topic": row[3], "created_at": row[4]}
            for row in cursor.fetchall()
        ]

    def get_history(self, session_id: str = "default", max_tokens: int = 3000) -> List[Dict]:
        """
        获取历史对话，构建 messages 列表（用于 LLM 上下文）
        自动截断到 max_tokens 以内
        """
        recent = self.get_recent(limit=50, session_id=session_id)
        recent.reverse()

        messages = []
        total_chars = 0

        for msg in recent:
            content = msg["content"]
            total_chars += len(content)
            if total_chars > max_tokens * 4:  # 粗略估算
                break
            messages.append({
                "role": msg["role"],
                "content": content,
            })

        return messages

    def search(self, keyword: str, limit: int = 10) -> List[Dict]:
        """关键词搜索记忆库"""
        cursor = self.conn.execute(
            "SELECT id, role, content, topic, created_at FROM conversation_memory "
            "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{keyword}%", limit)
        )
        return [
            {"id": row[0], "role": row[1], "content": row[2][:200],
             "topic": row[3], "created_at": row[4]}
            for row in cursor.fetchall()
        ]

    def get_topics(self, session_id: str = "default", limit: int = 50) -> List[Dict]:
        """获取对话话题列表（按时间分组）"""
        cursor = self.conn.execute(
            "SELECT topic, COUNT(*) as msg_count, MIN(created_at) as first_time, "
            "MAX(created_at) as last_time FROM conversation_memory "
            "WHERE session_id = ? GROUP BY topic ORDER BY last_time DESC LIMIT ?",
            (session_id, limit)
        )
        return [
            {"topic": row[0], "msg_count": row[1],
             "first_time": row[2], "last_time": row[3]}
            for row in cursor.fetchall()
        ]

    def clear_session(self, session_id: str = "default"):
        """清除指定会话的记忆"""
        self.conn.execute(
            "DELETE FROM conversation_memory WHERE session_id = ?",
            (session_id,)
        )
        self.conn.commit()

    def delete_message(self, message_id: int, session_id: str = "default"):
        """按 ID 删除一条对话记录（用于用户手动撤回聊天消息）"""
        self.conn.execute(
            "DELETE FROM conversation_memory WHERE id = ? AND session_id = ?",
            (message_id, session_id)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


# 全局实例
memory = ConversationMemory()


if __name__ == "__main__":
    # 测试
    mem = ConversationMemory()
    mem.add_message("user", "C30混凝土配合比是多少？", topic="材料查询")
    mem.add_message("assistant", "C30混凝土常规配合比：水泥350kg，砂680kg，石子1160kg，水175kg", topic="材料查询")

    print("最近对话:")
    for msg in mem.get_recent(limit=5):
        print(f"  [{msg['role']}] {msg['content'][:50]}...")

    print("\n话题列表:")
    for t in mem.get_topics():
        print(f"  {t['topic']} ({t['msg_count']}条消息)")

    print("\n搜索 '混凝土':")
    for r in mem.search("混凝土"):
        print(f"  [{r['role']}] {r['content'][:60]}...")

    mem.close()
