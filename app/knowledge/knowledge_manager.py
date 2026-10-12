"""知识库管理 — 前端手动选文件/文本上传"""

import os
from pathlib import Path
from typing import Optional, List, Dict

from app.knowledge.vector_store import VectorStore
from app.utils.config import settings


class KnowledgeManager:
    """
    知识库管理器
    - 用户手动选择文件上传（PDF/Word/Excel/TXT/图片）
    - 用户手动输入文本
    - 联网搜索结果自动缓存
    """

    def __init__(self):
        self.store = VectorStore()
        self.upload_dir = settings.ROOT_DIR / "data" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def add_text(self, name: str, content: str, source_type: str = "manual"):
        """手动添加文本到知识库"""
        self.store.add_text(name, content, source_type=source_type)

    def add_file(self, file_path: str, source_name: Optional[str] = None) -> Dict:
        """
        上传文件到知识库
        支持 PDF/Word/Excel/TXT/图片
        返回: {"status": "ok", "chunks": N, "content": "提取的文本"}
        """
        path = Path(file_path)
        if not path.exists():
            return {"status": "error", "message": f"文件不存在: {file_path}"}

        name = source_name or path.stem
        ext = path.suffix.lower()

        # 提取文本
        content = ""
        try:
            if ext == ".txt":
                content = path.read_text(encoding="utf-8", errors="replace")
            elif ext == ".md":
                content = path.read_text(encoding="utf-8", errors="replace")
            elif ext in [".pdf", ".docx", ".xlsx"]:
                # 使用 markitdown 或 python-docx 解析
                content = self._extract_from_doc(file_path, ext)
            elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                # 图片使用 OCR（预留接口）
                content = f"[图片文件: {path.name}，OCR待实现]"
            else:
                return {"status": "error", "message": f"不支持的文件类型: {ext}"}
        except Exception as e:
            return {"status": "error", "message": f"文件解析失败: {e}"}

        if not content.strip():
            return {"status": "error", "message": "文件内容为空"}

        # 复制到上传目录
        dest = self.upload_dir / f"{name}_{path.name}"
        import shutil
        shutil.copy2(str(path), str(dest))

        # 添加到向量库
        self.store.add_text(name, content, source_type="file_upload")

        # 更新知识源记录
        from app.database.connection import DatabaseManager
        from app.database.models import KnowledgeSource
        db = DatabaseManager()
        session = db.get_session()
        try:
            chunk_size = settings.KB_CHUNK_SIZE
            chunk_count = max(1, len(content) // chunk_size)
            ks = KnowledgeSource(
                name=name,
                source_type="file_upload",
                file_path=str(dest),
                content=content[:500],
                chunk_count=chunk_count,
            )
            session.add(ks)
            session.commit()
        finally:
            session.close()

        return {
            "status": "ok",
            "name": name,
            "chunks": chunk_count,
            "content_length": len(content),
            "message": f"成功添加知识源: {name}（{chunk_count}个分块）",
        }

    def _extract_from_doc(self, file_path: str, ext: str) -> str:
        """从办公文档中提取文本"""
        if ext == ".docx":
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif ext == ".xlsx":
            # 简单Excel读取
            import csv, io
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                lines = []
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        line = "\t".join(str(c) if c is not None else "" for c in row)
                        if line.strip():
                            lines.append(line)
                return "\n".join(lines)
            except ImportError:
                return f"[Excel文件: {Path(file_path).name}，需要安装openpyxl库解析]"
        elif ext == ".pdf":
            try:
                import PyPDF2
                text = []
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text() or "")
                return "\n".join(text)
            except ImportError:
                return f"[PDF文件: {Path(file_path).name}，需要安装PyPDF2库解析]"
        return ""

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索知识库"""
        return self.store.search(query, limit)

    def list_sources(self) -> List[Dict]:
        """列出所有知识源"""
        return self.store.list_sources()

    def delete_source(self, source_id: int):
        """删除知识源（source_id 为 vectors.db knowledge_source 表的 id）。

        双库同步：vectors.db 的 knowledge_source 元数据行与
        knowledge_embeddings 全部分块必须一起删除——否则列表/检索
        仍会出现已删除的源（UI 删除按钮传入的正是此 id）。
        兼容历史调用（SQLAlchemy KnowledgeSource.id）：先按向量库 id 删，
        未命中时按名字兜底删 SQLAlchemy 侧记录并清理同名分块。
        """
        # ① 向量库侧：删元数据行 + 同名全部分块
        row = self.store.conn.execute(
            "SELECT name FROM knowledge_source WHERE id = ?", (source_id,)
        ).fetchone()
        if row is not None:
            name = row[0]
            self.store.conn.execute(
                "DELETE FROM knowledge_embeddings WHERE source = ?", (name,))
            self.store.conn.execute(
                "DELETE FROM knowledge_source WHERE id = ?", (source_id,))
            self.store.conn.commit()
            self._unlink_named_file(name)
            return {"status": "ok", "message": f"已删除知识源: {name}"}

        # ② 兜底：source_id 不是向量库 id → 按业务库 id 删（历史行为）
        from app.database.connection import DatabaseManager
        from app.database.models import KnowledgeSource
        db = DatabaseManager()
        session = db.get_session()
        try:
            ks = session.query(KnowledgeSource).get(source_id)
            if ks:
                name = ks.name
                self.store.conn.execute(
                    "DELETE FROM knowledge_embeddings WHERE source = ?", (name,))
                self.store.conn.execute(
                    "DELETE FROM knowledge_source WHERE name = ?", (name,))
                self.store.conn.commit()
                if ks.file_path and Path(ks.file_path).exists():
                    Path(ks.file_path).unlink()
                session.delete(ks)
                session.commit()
                return {"status": "ok", "message": f"已删除知识源: {name}"}
            return {"status": "error", "message": "知识源不存在"}
        finally:
            session.close()

    def _unlink_named_file(self, name: str):
        """删除知识源名对应的上传文件（若在业务库登记过）。"""
        try:
            from app.database.connection import DatabaseManager
            from app.database.models import KnowledgeSource
            session = DatabaseManager().get_session()
            try:
                ks = session.query(KnowledgeSource).filter(
                    KnowledgeSource.name == name).first()
                if ks and ks.file_path and Path(ks.file_path).exists():
                    Path(ks.file_path).unlink()
                    session.delete(ks)
                    session.commit()
            finally:
                session.close()
        except Exception:
            pass  # 文件清理失败不阻断主流程


# 全局实例
knowledge = KnowledgeManager()
