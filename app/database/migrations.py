"""数据库迁移/初始化脚本"""

from app.database.connection import DatabaseManager


def _ensure_columns(db):
    """幂等加列：老库补新字段（Test-King M5 金额联动功能的 schema 迁移）。

    SQLAlchemy create_all 只建新表不改旧表，已有库必须 ALTER。
    """
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    try:
        have = {r[1] for r in conn.execute("PRAGMA table_info(change_order)")}
        for col, ddl in [
            ("days_change", "ALTER TABLE change_order ADD COLUMN days_change INTEGER"),
            ("contract_id", "ALTER TABLE change_order ADD COLUMN contract_id INTEGER"),
        ]:
            if col not in have:
                conn.execute(ddl)
        have_c = {r[1] for r in conn.execute("PRAGMA table_info(contract)")}
        for col, ddl in [
            ("contract_amount", "ALTER TABLE contract ADD COLUMN contract_amount FLOAT DEFAULT 0"),
            ("schedule_days", "ALTER TABLE contract ADD COLUMN schedule_days INTEGER DEFAULT 0"),
        ]:
            if col not in have_c:
                conn.execute(ddl)
        conn.commit()
    finally:
        conn.close()


def init_database():
    """初始化数据库，创建所有表"""
    db = DatabaseManager()
    db.init_db()
    _ensure_columns(db)
    print(f"[OK] 数据库初始化完成: {db.db_path}")
    return db


if __name__ == "__main__":
    init_database()
