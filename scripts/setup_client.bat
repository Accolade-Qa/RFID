@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo    AEPL RFID Laser Marking Utility - Client Prerequisite Setup
echo ====================================================================
echo.

:: Check for Administrative Privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges.
    echo Please right-click this file and select "Run as administrator".
    pause
    exit /b 1
)

:: Run PowerShell setup script with bypass policy
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_client.ps1"

echo.
echo Setup finished. Press any key to exit...
pause >nul
