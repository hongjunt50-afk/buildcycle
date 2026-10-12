# -*- coding: utf-8 -*-
"""一键安装的 Python 侧助手：创建桌面快捷方式 + 初始化数据目录

由「一键安装.bat」在依赖装好后调用。放在 Python 里做，是为了避开
cmd 批处理在中文路径 / 中文编码上的各种坑。
"""

import os
import sys
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "BuildCycle 建造全周期管控平台"
LAUNCHER = os.path.join(ROOT, "启动.bat")


def ok(msg):
    print("        OK  " + msg)


def warn(msg):
    print("        [!] " + msg)


def make_shortcut():
    """在桌面创建快捷方式。用 UTF-8 BOM 写 .ps1，PowerShell 5.1 能正确识别中文。"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        warn("找不到桌面目录，跳过快捷方式")
        return False
    lnk = os.path.join(desktop, APP_NAME + ".lnk")
    ps1 = os.path.join(tempfile.gettempdir(), "buildcycle_sc.ps1")

    # 图标优先用随包的 resources/app.ico（多尺寸，任务栏/大图标都清晰）；
    # 没有就退回用 启动.bat 的默认图标，不影响功能。
    ico = os.path.join(ROOT, "resources", "app.ico")
    icon = ico if os.path.exists(ico) else LAUNCHER

    script = (
        "$ErrorActionPreference = 'Stop'\n"
        "$s = New-Object -ComObject WScript.Shell\n"
        "$l = $s.CreateShortcut('{lnk}')\n"
        "$l.TargetPath = '{target}'\n"
        "$l.WorkingDirectory = '{wd}'\n"
        "$l.Description = '{desc}'\n"
        "$l.IconLocation = '{icon},0'\n"
        "$l.Save()\n"
    ).format(lnk=lnk, target=LAUNCHER, wd=ROOT, desc=APP_NAME, icon=icon)

    # UTF-8 with BOM：PowerShell 5.1 依据 BOM 判定编码，避免中文乱码
    with open(ps1, "w", encoding="utf-8-sig") as f:
        f.write(script)

    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0 or not os.path.exists(lnk):
            warn("快捷方式创建失败，可手动双击「启动.bat」")
            if r.stderr:
                print("        原因：" + r.stderr.strip()[:200])
            return False
        ok("桌面已生成图标：" + APP_NAME)
        return True
    except Exception as e:
        warn("快捷方式创建失败（%s），可手动双击「启动.bat」" % e)
        return False
    finally:
        try:
            os.remove(ps1)
        except OSError:
            pass


def init_data():
    """建立 data 目录并初始化数据库 / 向量库 / 记忆库"""
    data_dir = os.path.join(ROOT, "data")
    os.makedirs(os.path.join(data_dir, "uploads"), exist_ok=True)

    sys.path.insert(0, ROOT)
    try:
        from app.database.connection import DatabaseManager
        DatabaseManager().init_db()
        ok("业务数据库就绪")
    except Exception as e:
        warn("业务数据库初始化异常：%s" % e)
        return False

    try:
        from app.knowledge.vector_store import VectorStore
        VectorStore()
        ok("知识库向量库就绪")
    except Exception as e:
        warn("向量库初始化异常（不影响启动）：%s" % e)

    try:
        from app.knowledge.conversation_memory import memory  # noqa: F401
        ok("对话记忆库就绪")
    except Exception as e:
        warn("记忆库初始化异常（不影响启动）：%s" % e)

    return True


def main():
    make_shortcut()
    init_data()
    return 0


if __name__ == "__main__":
    sys.exit(main())
