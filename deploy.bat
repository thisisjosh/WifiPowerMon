rem Simple example deployment script to copy wifi_monitor.py to a remote server during development

@echo off
scp wifi_monitor.py josh@192.168.5.137:/home/josh/WifiPowerMon/
if %ERRORLEVEL% EQU 0 (
    echo File successfully copied to remote server
) else (
    echo Failed to copy file
    exit /b 1
)
