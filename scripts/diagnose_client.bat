@echo off
setlocal

echo ====================================================================
echo     AEPL RFID Laser Marking Utility - Environment Diagnostic
echo ====================================================================
echo.

set APP_DIR=%~dp0..
cd /d "%APP_DIR%"

:: Check if standalone exe exists
if exist "%APP_DIR%\dist\RFID_LASER\RFID_LASER_debug.exe" (
    echo Running Diagnostic on compiled debug executable...
    "%APP_DIR%\dist\RFID_LASER\RFID_LASER_debug.exe" --diag --only
) else if exist "%APP_DIR%\dist\RFID_LASER\RFID_LASER.exe" (
    echo Running Diagnostic on compiled production executable...
    "%APP_DIR%\dist\RFID_LASER\RFID_LASER.exe" --diag --only
) else if exist "%APP_DIR%\RFID_LASER.exe" (
    echo Running Diagnostic on root executable...
    "%APP_DIR%\RFID_LASER.exe" --diag --only
) else (
    echo Running Diagnostic with Python (auto-detecting 32/64-bit runtime)...
    python laser_main.py --diag --only
)

echo.
echo Diagnostic complete. Check activity.log for detailed output.
pause
