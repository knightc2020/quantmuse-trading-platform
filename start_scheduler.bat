@echo off
echo =====================================================
echo        QuantMuse 数据同步调度器
echo =====================================================
echo.
echo 启动每日数据同步服务...
echo 每晚8:00自动下载日线数据和龙虎榜数据
echo.
echo 按 Ctrl+C 停止调度器
echo.

cd /d "%~dp0"
python master_scheduler.py start

pause