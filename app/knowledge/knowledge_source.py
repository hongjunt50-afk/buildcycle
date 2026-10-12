"""知识源管理"""

from app.knowledge.vector_store import VectorStore


class KnowledgeSourceManager:
    """知识源管理"""

    def __init__(self):
        self.store = VectorStore()

    def add_manual(self, name: str, content: str):
        """手动添加知识源"""
        self.store.add_text(name, content)

    def search(self, query: str, limit: int = 5) -> list:
        """搜索知识库"""
        return self.store.search(query, limit)

    def list_sources(self) -> list:
        """列出所有知识源"""
        return self.store.list_sources()
