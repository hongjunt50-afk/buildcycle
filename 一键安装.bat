@echo off
chcp 936 >nul
cd /d "%~dp0"
title 工程项目全生命周期智能管控平台 - 免安装

echo.
echo  ==========================================================
echo     工程项目全生命周期智能管控平台
echo  ==========================================================
echo.
echo   本版本已经自带全部运行环境，不需要安装任何东西。
echo   现在为你创建桌面图标并打开软件，请稍等几秒...
echo.
echo   （桌面图标建好以后，以后从桌面双击就能用，
echo     不用再回到这个文件夹里找。）
echo.

rem 用随包运行时跑 install_helper.py：建桌面快捷方式 + 初始化数据目录。
rem 失败也无所谓，软件照样能开，所以这里不检查返回码。
if exist "%~dp0python\python.exe" (
    set "PYTHONPATH=%~dp0"
    set "PYTHONIOENCODING=utf-8:replace"
    "%~dp0python\python.exe" "%~dp0install_helper.py"
    set "PYTHONIOENCODING="
)

ping -n 3 127.0.0.1 >nul
call "%~dp0启动.bat"
exit /b 0
