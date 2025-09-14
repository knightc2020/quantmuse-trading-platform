@echo off
echo =====================================================
echo        手动数据同步工具
echo =====================================================
echo.

:menu
echo 请选择同步类型:
echo 1. 全部数据 (龙虎榜 + 日线数据)
echo 2. 仅龙虎榜数据
echo 3. 仅日线数据  
echo 4. 查看调度器状态
echo 5. 退出
echo.
set /p choice="请输入选项 (1-5): "

cd /d "%~dp0"

if "%choice%"=="1" (
    echo.
    echo 开始同步全部数据...
    python master_scheduler.py manual --type all
    echo.
    goto menu
)

if "%choice%"=="2" (
    echo.
    echo 开始同步龙虎榜数据...
    python master_scheduler.py manual --type dragon_tiger
    echo.
    goto menu
)

if "%choice%"=="3" (
    echo.
    echo 开始同步日线数据...
    python master_scheduler.py manual --type daily_quotes
    echo.
    goto menu
)

if "%choice%"=="4" (
    echo.
    echo 调度器执行状态:
    python master_scheduler.py status
    echo.
    goto menu
)

if "%choice%"=="5" (
    exit /b 0
)

echo 无效选项，请重新选择
goto menu