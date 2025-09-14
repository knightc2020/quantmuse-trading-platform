@echo off
setlocal
REM Run 50-stock perf test in background, logs written to logs/ directory
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_perf_50.ps1" -Date 2025-09-05 -CodesFile codes_50.txt -Limit 50
echo Started background performance test (50 stocks). Check logs\perf_50-*.log
endlocal

