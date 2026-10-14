@echo off
setlocal

echo ====================================================================
echo     AEPL RFID Laser Marking Utility - Environment Diagnostic
echo ====================================================================
echo.

set APP_DIR=%~dp0..
cd /d "%APP_DIR%"

:: Check if standalone exe exists
if exist "%APP_DIR%\dist\RFID_LASER\RFID_LASER.exe" (
    echo Running Diagnostic on compiled executable...
    "%APP_DIR%\dist\RFID_LASER\RFID_LASER.exe" --diag --only
) else if exist "%APP_DIR%\RFID_LASER.exe" (
    echo Running Diagnostic on root executable...
    "%APP_DIR%\RFID_LASER.exe" --diag --only
) else (
    echo Running Diagnostic via 32-bit Python runtime...
    py -3.8-32 laser_main.py --diag --only
)

echo.
echo Diagnostic complete. Check activity.log for detailed output.
pause
