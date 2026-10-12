"""Qt 后台任务执行器 — 让网络/IO 请求离开 GUI 主线程

平台"莫名卡住"的根因：urllib 请求（30 秒超时）在主线程里跑，
网络一慢整个界面冻结。本模块提供统一的后台执行 + 主线程回调。
"""

import traceback

from PySide6.QtCore import QObject, QThread, Signal


class _Worker(QObject):
    finished = Signal(object)   # 成功：返回值
    failed = Signal(str)        # 失败：错误信息

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            result = self._fn()
            self.finished.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(f"{type(e).__name__}: {e}")


# 运行中的任务注册表：QThread/QObject 绝不能被 Python GC 回收，
# 否则 C++ 线程还在跑、宿主对象没了 → 0xC0000409 硬崩（已实测复现）。
_live = set()


def run_in_thread(fn, on_done=None, on_error=None):
    """
    在后台 QThread 里执行 fn()，结束后在主线程触发回调。

    - on_done(result)  fn 正常返回时调用
    - on_error(str)    fn 抛异常时调用（不传则静默，仅打日志）
    """
    thread = QThread()
    worker = _Worker(fn)
    worker.moveToThread(thread)

    def _cleanup():
        _live.discard((thread, worker))
        thread.quit()

    def _ok(result):
        try:
            if on_done:
                on_done(result)
        finally:
            _cleanup()

    def _err(msg):
        try:
            if on_error:
                on_error(msg)
            else:
                traceback.print_exc()
        finally:
            _cleanup()

    thread.started.connect(worker.run)
    worker.finished.connect(_ok)
    worker.failed.connect(_err)

    _live.add((thread, worker))   # 保活：任务结束才释放
    thread.start()
    return thread, worker
