@echo off
chcp 65001 >nul
cd /d "%~dp0"

:menu
cls
echo ============================================
echo        个人 PM 管理系统
echo ============================================
echo   1  启动服务（单进程，推荐）
echo   2  开发模式启动（需 Node，热更新）
echo   3  停止服务
echo   4  重启服务
echo   5  查看状态
echo   0  退出
echo ============================================
set /p choice=请输入选项后回车: 

if "%choice%"=="1" (
    python start.py serve
) else if "%choice%"=="2" (
    python start.py start
) else if "%choice%"=="3" (
    python start.py stop
) else if "%choice%"=="4" (
    python start.py restart
) else if "%choice%"=="5" (
    python start.py status
) else if "%choice%"=="0" (
    exit /b 0
) else (
    echo 无效选项，请重新输入
    timeout /t 2 >nul
    goto menu
)

echo.
pause
goto menu