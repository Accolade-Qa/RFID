@echo off
setlocal enabledelayedexpansion

title AEPL RFID Laser Marking Utility

echo ====================================================================
echo        AEPL RFID Laser Marking Utility — Auto Launcher
echo ====================================================================
echo.

:: 1. Detect PC Operating System Architecture
set OS_ARCH=32-bit (x86)
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set OS_ARCH=64-bit (x64)
if "%PROCESSOR_ARCHITEW6432%"=="AMD64" set OS_ARCH=64-bit (x64 via WOW64)
echo [*] Detected PC Operating System Architecture: %OS_ARCH%

:: 2. If compiled standalone executable exists, launch it directly
:: (32-bit PE runs natively on 32-bit Windows and via WOW64 on 64-bit Windows)
if exist "%~dp0dist\RFID_LASER\RFID_LASER.exe" (
    echo [*] Launching compiled executable: dist\RFID_LASER\RFID_LASER.exe
    start "" "%~dp0dist\RFID_LASER\RFID_LASER.exe" %*
    exit /b 0
)

if exist "%~dp0RFID_LASER.exe" (
    echo [*] Launching standalone executable: RFID_LASER.exe
    start "" "%~dp0RFID_LASER.exe" %*
    exit /b 0
)

:: 3. Check for 32-bit Python runtime
py -3.8-32 --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Launching with Python 3.8 32-bit runtime...
    py -3.8-32 "%~dp0laser_main.py" %*
    exit /b %errorlevel%
)

:: 4. Fallback: Launch with default Python (auto-detector handles 64-bit routing)
echo [*] Launching with Python (with auto-architecture detection)...
python "%~dp0laser_main.py" %*
