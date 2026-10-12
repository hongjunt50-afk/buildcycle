"""离线/P2P 协同同步引擎（来自 Massing 离线优先设计）"""

import json
import sqlite3
import hashlib
import shutil
import socket
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Callable

from app.utils.config import settings


class SyncEngine:
    """
    离线/P2P 协同同步引擎
    - 本地SQLite变更追踪
    - 局域网P2P同步（TCP）
    - 离线操作→恢复联网后自动同步
    - 冲突检测与解决
    """

    def __init__(self):
        self.db_path = settings.DB_PATH
        self.sync_dir = Path(settings.DB_PATH).parent / "sync"
        self.sync_dir.mkdir(parents=True, exist_ok=True)

        # 同步日志
        self.sync_log_path = self.sync_dir / "sync_log.json"
        self.peers_path = self.sync_dir / "peers.json"

        # 配置
        self.node_id = self._get_node_id()
        self.port = 19876  # P2P 端口
        self.server = None
        self.running = False

    def _get_node_id(self) -> str:
        """获取节点唯一标识"""
        node_file = self.sync_dir / "node_id"
        if node_file.exists():
            return node_file.read_text().strip()
        node_id = hashlib.md5(str(Path.home()).encode()).hexdigest()[:8]
        node_file.write_text(node_id)
        return node_id

    # ── 变更追踪 ──

    def _get_table_changes(self, table_name: str, since: str = None) -> List[Dict]:
        """获取表的变更记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # 检查是否有 updated_at 字段
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row["name"] for row in cursor.fetchall()]

            if "updated_at" not in columns:
                return []

            if since:
                cursor.execute(
                    f"SELECT * FROM {table_name} WHERE updated_at > ?",
                    (since,)
                )
            else:
                cursor.execute(f"SELECT * FROM {table_name}")

            rows = []
            for row in cursor.fetchall():
                rows.append(dict(row))
            return rows
        finally:
            conn.close()

    def export_changes(self, since: str = None) -> Dict:
        """导出变更数据包"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()
                  if not row[0].startswith("sqlite_")]
        conn.close()

        changes = {}
        for table in tables:
            rows = self._get_table_changes(table, since)
            if rows:
                changes[table] = rows

        return {
            "node_id": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "since": since,
            "changes": changes,
        }

    def import_changes(self, data: Dict) -> Dict:
        """导入变更数据包"""
        if data["node_id"] == self.node_id:
            return {"status": "skipped", "reason": "自身数据"}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        imported = 0
        conflicts = 0

        for table_name, rows in data.get("changes", {}).items():
            for row in rows:
                try:
                    # 检查是否存在
                    row_id = row.get("id")
                    if row_id:
                        cursor.execute(
                            f"SELECT id FROM {table_name} WHERE id = ?",
                            (row_id,)
                        )
                        existing = cursor.fetchone()

                        if existing:
                            # 冲突检测：比较更新时间
                            if "updated_at" in row:
                                cursor.execute(
                                    f"SELECT updated_at FROM {table_name} WHERE id = ?",
                                    (row_id,)
                                )
                                local_time = cursor.fetchone()
                                if local_time and row["updated_at"] > local_time[0]:
                                    # 远端更新，覆盖本地
                                    self._update_row(cursor, table_name, row)
                                    imported += 1
                                else:
                                    conflicts += 1
                            else:
                                conflicts += 1
                        else:
                            # 新增
                            self._insert_row(cursor, table_name, row)
                            imported += 1
                except Exception as e:
                    conflicts += 1

        conn.commit()
        conn.close()

        # 记录同步日志
        self._log_sync(data["node_id"], imported, conflicts)

        return {
            "status": "ok",
            "imported": imported,
            "conflicts": conflicts,
        }

    def _insert_row(self, cursor, table: str, row: Dict):
        columns = [k for k in row.keys() if k != "id" or row["id"] is not None]
        placeholders = ["?" for _ in columns]
        values = [row.get(k) for k in columns]
        cursor.execute(
            f"INSERT OR IGNORE INTO {table} ({','.join(columns)}) VALUES ({','.join(placeholders)})",
            values
        )

    def _update_row(self, cursor, table: str, row: Dict):
        columns = [k for k in row.keys() if k != "id"]
        set_clause = ",".join(f"{k}=?" for k in columns)
        values = [row.get(k) for k in columns] + [row["id"]]
        cursor.execute(
            f"UPDATE {table} SET {set_clause} WHERE id=?",
            values
        )

    def _log_sync(self, peer_id: str, imported: int, conflicts: int):
        """记录同步日志"""
        log = {
            "timestamp": datetime.now().isoformat(),
            "peer_id": peer_id,
            "imported": imported,
            "conflicts": conflicts,
        }
        logs = []
        if self.sync_log_path.exists():
            logs = json.loads(self.sync_log_path.read_text())
        logs.append(log)
        if len(logs) > 100:
            logs = logs[-100:]
        self.sync_log_path.write_text(json.dumps(logs, ensure_ascii=False, indent=2))

    # ── P2P 网络同步 ──

    def start_server(self):
        """启动 P2P 服务端（后台线程）"""
        if self.running:
            return

        self.running = True
        self.server = threading.Thread(target=self._server_loop, daemon=True)
        self.server.start()
        print(f"[P2P] 同步服务启动，端口: {self.port}")

    def _server_loop(self):
        """P2P 服务端循环"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", self.port))
            sock.listen(5)
            sock.settimeout(1.0)

            while self.running:
                try:
                    client, addr = sock.accept()
                    handler = threading.Thread(
                        target=self._handle_client,
                        args=(client, addr),
                        daemon=True
                    )
                    handler.start()
                except socket.timeout:
                    continue
        except Exception as e:
            print(f"[P2P] 服务端错误: {e}")
        finally:
            sock.close()

    def _handle_client(self, client, addr):
        """处理客户端请求"""
        try:
            data = client.recv(65536)
            request = json.loads(data.decode())

            if request.get("action") == "sync_pull":
                # 返回变更数据
                since = request.get("since")
                changes = self.export_changes(since)
                client.send(json.dumps(changes).encode())

            elif request.get("action") == "sync_push":
                # 接收变更数据
                result = self.import_changes(request.get("data", {}))
                client.send(json.dumps(result).encode())

        except Exception as e:
            try:
                client.send(json.dumps({"error": str(e)}).encode())
            except:
                pass
        finally:
            client.close()

    def sync_with_peer(self, peer_ip: str, port: int = None) -> Dict:
        """与指定节点同步"""
        port = port or self.port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer_ip, port))

            # 发送拉取请求
            request = {
                "action": "sync_pull",
                "since": None,  # 全量同步
            }
            sock.send(json.dumps(request).encode())

            # 接收响应
            response = sock.recv(65536)
            peer_data = json.loads(response.decode())

            # 导入对方数据
            result = self.import_changes(peer_data)

            sock.close()
            return {
                "status": "ok",
                "peer": peer_ip,
                "imported": result["imported"],
                "conflicts": result["conflicts"],
            }

        except Exception as e:
            return {"status": "error", "peer": peer_ip, "error": str(e)}

    def discover_peers(self) -> List[str]:
        """发现局域网内的其他节点（UDP广播）"""
        peers = []
        try:
            broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_sock.settimeout(2)
            broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            message = json.dumps({
                "action": "discover",
                "node_id": self.node_id,
                "port": self.port,
            }).encode()

            broadcast_sock.sendto(message, ("255.255.255.255", self.port))

            try:
                while True:
                    data, addr = broadcast_sock.recvfrom(1024)
                    response = json.loads(data.decode())
                    if response.get("node_id") != self.node_id:
                        peers.append({
                            "ip": addr[0],
                            "port": response.get("port", self.port),
                            "node_id": response.get("node_id"),
                        })
            except socket.timeout:
                pass

            broadcast_sock.close()
        except Exception as e:
            pass

        return peers

    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        logs = []
        if self.sync_log_path.exists():
            logs = json.loads(self.sync_log_path.read_text())

        peers = []
        if self.peers_path.exists():
            peers = json.loads(self.peers_path.read_text())

        return {
            "node_id": self.node_id,
            "port": self.port,
            "running": self.running,
            "sync_logs": logs[-10:],
            "known_peers": peers,
        }


if __name__ == "__main__":
    sync = SyncEngine()
    print(f"节点ID: {sync.node_id}")
    print(f"数据库: {sync.db_path}")
    print(f"同步目录: {sync.sync_dir}")

    # 导出变更
    changes = sync.export_changes()
    table_count = len(changes.get("changes", {}))
    print(f"可同步表: {table_count} 张")

    # 启动服务
    sync.start_server()
    print(f"P2P 服务已启动，端口 {sync.port}")
    print(f"状态: {sync.get_sync_status()}")

    # 停止
    sync.running = False
