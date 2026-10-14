# ==============================================================================
# AEPL RFID Laser Marking Utility — Client Automated Prerequisite Setup
# Automatically detects OS Architecture (32-bit vs 64-bit) & Installs Dependencies
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$ForceDownload
)

$ErrorActionPreference = "Continue"

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "    AEPL RFID Laser Marking Utility - Client System Setup     " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan

# 1. Detect Architecture & OS
$is64Bit = [Environment]::Is64BitOperatingSystem
$osArch = if ($is64Bit) { "64-bit (x64)" } else { "32-bit (x86)" }
$osVersion = (Get-WmiObject -Class Win32_OperatingSystem).Caption

Write-Host "`n[*] Detecting Client Environment:" -ForegroundColor Yellow
Write-Host "    - Operating System : $osVersion"
Write-Host "    - OS Architecture  : $osArch"
Write-Host "    - Target Executable: 32-bit (PE32) required by EzCAD 2.14.11 DLLs"

# Note on Architecture:
# Even on 64-bit Windows, RFID_LASER.exe runs as a 32-bit process inside WOW64,
# so the 32-bit (x86) Visual C++ Runtimes are MANDATORY on BOTH 32-bit and 64-bit machines!

$tempDir = Join-Path $env:TEMP "AEPL_Prereq_Setup"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Function to download and run installer
function Install-Prerequisite {
    param (
        [string]$Name,
        [string]$Url,
        [string]$FileName,
        [string]$InstallArgs = "/install /quiet /norestart"
    )

    $targetFile = Join-Path $tempDir $FileName
    Write-Host "`n[*] Processing: $Name" -ForegroundColor Yellow

    if ((Test-Path $targetFile) -and (-not $ForceDownload)) {
        Write-Host "    [FOUND] Installer already cached at $targetFile" -ForegroundColor Green
    } else {
        Write-Host "    [DOWNLOADING] From: $Url" -ForegroundColor Cyan
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls
            (New-Object System.Net.WebClient).DownloadFile($Url, $targetFile)
            Write-Host "    [DOWNLOAD SUCCESS] Saved to: $targetFile" -ForegroundColor Green
        } catch {
            Write-Host "    [DOWNLOAD FAILED] Could not auto-download: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "    [ACTION REQUIRED] Please manually download $Name from:" -ForegroundColor Yellow
            Write-Host "    $Url" -ForegroundColor White
            return
        }
    }

    Write-Host "    [INSTALLING] Running installer silently..." -ForegroundColor Cyan
    try {
        $process = Start-Process -FilePath $targetFile -ArgumentList $InstallArgs -Wait -PassThru
        if ($process.ExitCode -eq 0 -or $process.ExitCode -eq 3010) {
            Write-Host "    [PASS] $Name installed successfully! (ExitCode: $($process.ExitCode))" -ForegroundColor Green
        } else {
            Write-Host "    [WARN] $Name installer returned code $($process.ExitCode). (May already be installed)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    [ERROR] Failed to execute installer: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 2. Install Visual C++ 2015-2022 (x86) — Mandatory for 32-bit Python 3.8 / EzCAD
Install-Prerequisite `
    -Name "Microsoft Visual C++ 2015-2022 Redistributable (x86 - 32-bit)" `
    -Url "https://aka.ms/vs/17/release/vc_redist.x86.exe" `
    -FileName "vc_redist.x86.exe" `
    -InstallArgs "/install /quiet /norestart"

# 3. If OS is 64-bit, also install Visual C++ 2015-2022 (x64) for system tools
if ($is64Bit) {
    Install-Prerequisite `
        -Name "Microsoft Visual C++ 2015-2022 Redistributable (x64 - 64-bit)" `
        -Url "https://aka.ms/vs/17/release/vc_redist.x64.exe" `
        -FileName "vc_redist.x64.exe" `
        -InstallArgs "/install /quiet /norestart"
}

# 4. Install Visual C++ 2010 SP1 (x86) — Required by older EzCAD 2.14 DLLs
Install-Prerequisite `
    -Name "Microsoft Visual C++ 2010 SP1 Redistributable (x86)" `
    -Url "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-A094-B6A430A6BFFC/vcredist_x86.exe" `
    -FileName "vcredist_2010_x86.exe" `
    -InstallArgs "/q /norestart"

# 5. Check USB-to-UART Serial Ports (RFID Reader)
Write-Host "`n[*] Checking Hardware Serial Ports (RFID Reader):" -ForegroundColor Yellow
$serialPorts = [System.IO.Ports.SerialPort]::GetPortNames()
if ($serialPorts -and $serialPorts.Count -gt 0) {
    Write-Host "    [PASS] Detected COM Ports: $($serialPorts -join ', ')" -ForegroundColor Green
} else {
    Write-Host "    [NOTICE] No COM Ports currently detected." -ForegroundColor Yellow
    Write-Host "             Please connect the RFID Reader USB and ensure the USB-UART driver is installed:"
    Write-Host "             - FTDI Driver: https://ftdichip.com/drivers/vcp-drivers/"
    Write-Host "             - Silicon Labs CP210x Driver: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers"
}

# 6. Check EzCAD USB Board
Write-Host "`n[*] Checking EzCAD USB Controller (LMC1):" -ForegroundColor Yellow
$ezcadDevice = Get-WmiObject Win32_PnPEntity | Where-Object { $_.Name -match "EzCAD|LMC|Laser|BJJCZ" -or $_.HardwareID -match "VID_0483|VID_10C4" }
if ($ezcadDevice) {
    Write-Host "    [PASS] Detected EzCAD Controller: $($ezcadDevice.Name)" -ForegroundColor Green
} else {
    Write-Host "    [NOTICE] EzCAD hardware board not detected on USB." -ForegroundColor Yellow
    Write-Host "             Connect the laser controller board via USB and install the driver from EzCAD's \Drivers\ folder."
}

Write-Host "`n==============================================================" -ForegroundColor Cyan
Write-Host "               Prerequisite Setup Completed!                  " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
