"""BuildCycle 建造全周期管控平台 — 入口"""

import sys
import os
import traceback

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG_NAME = "运行日志.txt"


def _log_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", LOG_NAME)


def write_log(text: str):
    """把错误写进 data/运行日志.txt，方便用户直接把这个文件发给开发者。"""
    try:
        p = _log_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(text + "\n")
        return p
    except Exception:
        return None


def show_fatal(title: str, detail: str):
    """弹出一个用户看得懂的窗口；弹不出来就退回打印。"""
    hint = (
        "程序启动时遇到问题，已把详细信息写进：\n"
        "    data\\运行日志.txt\n\n"
        "请把那个文件发给开发者，或直接截图发过去。\n\n"
        "──────────────────────────────\n"
    )
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("启动失败")
        box.setText(hint)
        box.setDetailedText(detail)
        box.exec()
    except Exception:
        try:
            sys.stderr.write(hint + detail + "\n")
        except Exception:
            pass


def _redirect_streams_when_headless():
    """用 pythonw.exe 启动时没有控制台，sys.stdout/stderr 是 None。

    此时把输出重定向到 data/运行日志.txt，既不会丢信息，也不会让
    某个 print 撞上 None 而崩掉。
    """
    if sys.stdout is not None and sys.stderr is not None:
        return None
    try:
        p = _log_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        f = open(p, "a", encoding="utf-8", buffering=1)
        sys.stdout = f
        sys.stderr = f
        return f
    except Exception:
        return None


def bootstrap():
    """启动前自检：确保数据目录存在

    用户可能手动删掉 data/ 目录（或从没装过），此时直接用会崩。
    这里统一兜底重建，让程序永远能起来。
    """
    from app.utils.config import settings
    from pathlib import Path

    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def init_only():
    """仅初始化数据库（供一键安装调用，不启动界面）"""
    bootstrap()
    from app.database.connection import DatabaseManager
    db = DatabaseManager()
    db.init_db()
    print("        OK  数据库就绪")
    return 0


def main():
    """启动应用"""
    bootstrap()
    from PySide6.QtWidgets import QApplication
    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("buildcycle")
    app.setOrganizationName("buildcycle")
    app.setStyle("Fusion")

    # 运行时未捕获异常：写日志，并提示用户，而不是直接闪退
    def _hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        p = write_log(text)
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, "程序出错",
                "程序遇到一个错误，操作可能没生效。\n"
                + ("详细信息已写入：data\\运行日志.txt\n" if p else "")
                + "可以把这个文件发给开发者。")
        except Exception:
            pass

    sys.excepthook = _hook

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    # 用 pythonw.exe 静默启动时没有控制台，先把输出接到日志文件
    _headless_log = _redirect_streams_when_headless()
    # 控制台里显式设成 UTF-8；老机器的 GBK 控制台遇到生僻字会抛异常
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if "--init-only" in sys.argv:
        sys.exit(init_only())
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        detail = traceback.format_exc()
        write_log(detail)
        show_fatal("启动失败", detail)
        sys.exit(1)
    finally:
        if _headless_log is not None:
            try:
                _headless_log.close()
            except Exception:
                pass
