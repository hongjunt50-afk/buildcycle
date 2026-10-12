@echo off
chcp 936 >nul
cd /d "%~dp0"
title 工程项目全生命周期智能管控平台

set "PY="

rem 首选随包附带的便携运行时（自带 Python + 全部依赖，无需安装）
rem 探测必须用 python.exe：pythonw.exe 没有控制台，重定向和错误码都不可靠，
rem 会把「缺依赖」误判成「可用」，然后静默拉起一个起不来的窗口。
if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" -c "import PySide6" >nul 2>nul
    if not errorlevel 1 set "PY=%~dp0python\python.exe"
)

rem 便携运行时缺失时，退回本机开发用的 .venv（开发机双击本项目时走这条）
if not defined PY if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -c "import PySide6" >nul 2>nul
    if not errorlevel 1 set "PY=%~dp0.venv\Scripts\python.exe"
)

rem 便携运行时缺失时，回退到本机已装的 Python（同样必须能 import PySide6）
if not defined PY (
    for %%P in (python.exe) do if exist "%%~$PATH:P" (
        "%%~$PATH:P" -c "import PySide6" >nul 2>nul
        if not errorlevel 1 set "PY=%%~$PATH:P"
    )
)

if not defined PY (
    echo.
    echo   [X] 运行环境缺失或已损坏
    echo.
    echo   这个文件夹可能被移动过、解压不完整，或者 python 子文件夹被删了。
    echo   请重新完整解压收到的压缩包后再试。
    echo.
    pause
    exit /b 1
)

rem 用同目录的 pythonw.exe 启动，避免多留一个黑色命令行窗口
set "LAUNCH=%PY%"
set "TRY=%PY:python.exe=pythonw.exe%"
if not "%TRY%"=="%PY%" if exist "%TRY%" set "LAUNCH=%TRY%"

echo 正在启动 工程项目全生命周期智能管控平台，请稍等几秒...
set "PYTHONPATH=%~dp0"
start "" "%LAUNCH%" "%~dp0main.py"
exit /b 0
