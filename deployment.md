# AEPL RFID Laser Marking Utility — Deployment & Client Configuration Guide

This guide provides end-to-end instructions for deploying, configuring, and operating the **AEPL RFID Laser Marking Utility** on client PCs running **Windows 7 (32-bit / 64-bit)** with **EzCAD 2.14.11**.

---

## 📋 Table of Contents
1. [How It Works (System Architecture)](#1-how-it-works-system-architecture)
2. [Prerequisites by Client Architecture (32-bit vs 64-bit)](#2-prerequisites-by-client-architecture-32-bit-vs-64-bit)
3. [Automated Client Setup Script (Command Flow)](#3-automated-client-setup-script-command-flow)
4. [Verifying & Diagnosing the Executable (Tracking Errors & Live Logs)](#4-verifying--diagnosing-the-executable-tracking-errors--live-logs)
5. [Hardware Connections & Device Drivers](#5-hardware-connections--device-drivers)
6. [EzCAD Template Configuration (`test.ezd`)](#6-ezcad-template-configuration-testezd)
7. [Deploying Application Files to Client PC](#7-deploying-application-files-to-client-pc)
8. [First-Time Software Configuration](#8-first-time-software-configuration)
9. [Operator Workflow Modes](#9-operator-workflow-modes)
10. [Troubleshooting & Error Codes Reference](#10-troubleshooting--error-codes-reference)

---

## 1. How It Works (System Architecture)

```
┌─────────────────┐       UART (COM Port)       ┌──────────────────────────────┐
│   RFID Reader   │ ◄─────────────────────────► │  RFID Laser Marking Utility  │
│   (AEPL VLTD)   │   24 11 01 00 8B FE 23      │  RFID_LASER.exe / _debug.exe │
└─────────────────┘      (24-char Tag ID)       └──────────────┬───────────────┘
                                                               │
                                         Direct 32-bit DLL     │ Calls MarkEzd.dll:
                                         In-Process API Calls  │ 1. lmc1_LoadEzdFile('test.ezd')
                                                               │ 2. lmc1_ChangeTextByName('t1', TagID)
                                                               │ 3. lmc1_Mark(0)
                                                               ▼
                                                ┌──────────────────────────────┐
                                                │   EzCAD 2.14.11 Controller   │
                                                │    (LMC1 Laser Board / USB)  │
                                                └──────────────┬───────────────┘
                                                               │ Galvo & Laser Signal
                                                               ▼
                                                ┌──────────────────────────────┐
                                                │     Laser Marking Machine    │
                                                │    (Prints Tag ID on Tag)    │
                                                └──────────────────────────────┘
```

1. **Read Tag**: The utility sends command `24 11 01 00 8B FE 23` over serial UART to the RFID reader.
2. **Decode**: The RFID reader scans the tag and returns the binary frame; the utility verifies the frame boundary and extracts the 24-character hexadecimal Tag ID.
3. **Substitute**: The utility calls `MarkEzd.dll` (`lmc1_ChangeTextByName`) to dynamically change the text entity named **`t1`** in `test.ezd` to the scanned Tag ID.
4. **Mark**: The utility calls `lmc1_Mark(0)` to trigger the galvo mirrors and laser source to engrave the Tag ID onto the physical tag.

---

## 2. Prerequisites by Client Architecture (32-bit vs 64-bit)

### ⚙️ Auto-Detection & Dual-Architecture Support:
The application provides full support for **both 32-bit and 64-bit PCs** with automatic architecture detection:
1. **`run.bat` (One-Click Auto-Launcher)**:
   - Automatically detects whether the client PC is 32-bit (`x86`) or 64-bit (`AMD64`/`x64`).
   - Automatically launches `RFID_LASER.exe` or routes to the correct runtime.
2. **`main.py` / `laser_main.py` (Source Auto-Relauncher)**:
   - When run on a 64-bit machine using 64-bit Python, the script auto-detects the 64-bit process, searches for 32-bit Python (`py -3.8-32` or local install paths), and **automatically re-launches under 32-bit mode**.
   - If no 32-bit Python is present, it auto-enables **Simulation Mode** so RFID reading and template testing continue without crashing.
3. **Compiled Executables (`RFID_LASER.exe` & `RFID_LASER_debug.exe`)**:
   - Compiled as 32-bit PE binaries.
   - Run natively on **32-bit Windows** and run seamlessly on **64-bit Windows** via the built-in Windows **WOW64** subsystem.

### ⚠️ Critical Architecture Note:
Because EzCAD 2.14.11 and `MarkEzd.dll` are **32-bit (PE32) binaries**, the laser driver requires a 32-bit execution environment.
* **On a 32-bit Windows machine (x86)**: The process runs natively and requires **32-bit (x86)** runtimes in `C:\Windows\System32`.
* **On a 64-bit Windows machine (x64)**: The process runs inside the **WOW64** subsystem and requires **32-bit (x86)** runtimes in `C:\Windows\SysWOW64`.
* **Conclusion**: **The 32-bit (x86) Visual C++ Runtimes are MANDATORY on BOTH 32-bit and 64-bit client machines!**

### Dependency Matrix:

| Component | 32-bit Client PC (x86) | 64-bit Client PC (x64) | Purpose |
| :--- | :--- | :--- | :--- |
| **VC++ 2015–2022 (x86)** | **Required** | **Required** | Needed by Python runtime and companion DLLs. |
| **VC++ 2015–2022 (x64)** | *Not Applicable* | Optional | For 64-bit system tools. |
| **VC++ 2010 SP1 (x86)** | **Required** | **Required** | Needed by `DataMgr.dll` and `Lmc1.dll`. |
| **Windows 7 Update** | KB2533623 / KB2999226 | KB2533623 / KB2999226 | Universal C Runtime for Windows 7. |
| **USB-UART Driver** | 32-bit CP210x / FTDI / PL2303 | 64-bit CP210x / FTDI / PL2303 | COM Port communication with RFID reader. |
| **EzCAD LMC1 Driver** | 32-bit BJJCZ Driver | 64-bit BJJCZ Driver | USB laser controller board driver. |
| **Python Runtime** | **NOT NEEDED** | **NOT NEEDED** | Standalone pre-compiled executable. |

---

## 3. Automated Client Setup Script (Command Flow)

We have provided automated scripts located in `scripts/` inside the application package to detect client architecture, download missing Microsoft packages, and configure the system.

### Option A: One-Click Batch Setup (Recommended)
1. On the client PC, navigate to:
   ```
   C:\AEPL\RFID_LASER\scripts\
   ```
2. Right-click **`setup_client.bat`** -> select **"Run as administrator"**.
3. The script automatically:
   * Detects whether the OS is 32-bit or 64-bit.
   * Downloads and installs Microsoft Visual C++ 2015–2022 Redistributable (x86).
   * Downloads and installs Microsoft Visual C++ 2010 SP1 Redistributable (x86).
   * Verifies serial COM ports and EzCAD hardware board presence.

### Option B: Manual PowerShell Command Flow
If running commands manually on the client machine via PowerShell (Run as Administrator):

```powershell
# 1. Set TLS 1.2 for secure downloads
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11 -bor [Net.SecurityProtocolType]::Tls

# 2. Download and install Visual C++ 2015-2022 x86 (Mandatory for both 32-bit and 64-bit OS)
$vc2022Url = "https://aka.ms/vs/17/release/vc_redist.x86.exe"
$vc2022Path = "$env:TEMP\vc_redist.x86.exe"
(New-Object System.Net.WebClient).DownloadFile($vc2022Url, $vc2022Path)
Start-Process -FilePath $vc2022Path -ArgumentList "/install /quiet /norestart" -Wait

# 3. Download and install Visual C++ 2010 SP1 x86 (Mandatory for EzCAD DLLs)
$vc2010Url = "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-A094-B6A430A6BFFC/vcredist_x86.exe"
$vc2010Path = "$env:TEMP\vcredist_2010_x86.exe"
(New-Object System.Net.WebClient).DownloadFile($vc2010Url, $vc2010Path)
Start-Process -FilePath $vc2010Path -ArgumentList "/q /norestart" -Wait
```

---

## 4. Verifying & Diagnosing the Executable (Tracking Errors & Live Logs)

When deploying to a client workstation, you need complete visibility into DLL loading, COM port communication, and any runtime errors.

### Tool 1: Live Terminal Debug Executable (`RFID_LASER_debug.exe`)
Inside the application folder, we provide two executables:
* **`RFID_LASER.exe`**: Clean production GUI without terminal window.
* **`RFID_LASER_debug.exe`**: **Diagnostic version with attached live Command Prompt window**.
  * Displays every UART transmit (`TX`) and receive (`RX`) byte stream in real time.
  * Displays exact return codes from `MarkEzd.dll` (`lmc1_Initial2`, `lmc1_ChangeTextByName`, `lmc1_Mark`).
  * If a crash or DLL error occurs, the complete Python traceback is printed directly on screen.

### Tool 2: One-Click Environment Diagnostic (`scripts\diagnose_client.bat`)
Run this tool before production to verify system health:
1. Double-click `scripts\diagnose_client.bat` or run:
   ```cmd
   RFID_LASER_debug.exe --diag --only
   ```
2. It outputs an automated checklist:
   ```text
   [*] Python Process Architecture: 32-bit
       [PASS] 32-bit architecture matches EzCAD 2.14.11 requirements.
   [*] Checking Required EzCAD Companion Files:
       [PASS] MarkEzd.dll     (155,648 bytes)
       [PASS] Lmc1.dll        (524,288 bytes)
       [PASS] DataMgr.dll     (1,343,488 bytes)
       [PASS] mathlib.dll     (172,032 bytes)
       [PASS] LMCMIO.dll      (36,864 bytes)
       [PASS] EZCAD.CFG       (11,388 bytes)
       [PASS] test.ezd        (1,705,161 bytes)
   [*] Testing MarkEzd.dll Loadability:
       [PASS] MarkEzd.dll loaded successfully into process memory.
       [PASS] Symbol found: lmc1_Initial2
       [PASS] Symbol found: lmc1_LoadEzdFile
       [PASS] Symbol found: lmc1_ChangeTextByName
       [PASS] Symbol found: lmc1_Mark
       [PASS] Symbol found: lmc1_Close
   [*] Scanning Available Serial Ports (RFID Reader):
       [FOUND] COM6: Prolific PL2303GT USB Serial COM Port (COM6)
   ```

### Tool 3: Persistent Crash & Activity Logs
* **`activity.log`**: Records all events with timestamps (app startup, serial connections, tag scans, template updates, laser mark results).
* **`crash.log`**: Automatically captures any unhandled fatal exception and stack trace if an unexpected error occurs.

---

## 5. Hardware Connections & Device Drivers

1. **Connect RFID Reader**:
   * Plug the RFID reader's USB cable into the PC.
   * Open **Device Manager** (`devmgmt.msc`) -> expand **Ports (COM & LPT)**.
   * Note the allocated port number (e.g. `COM3` or `COM6`).
2. **Connect Laser Controller (LMC1)**:
   * Plug the EzCAD USB controller cable into the PC and turn on the laser machine power supply.
   * In **Device Manager**, verify that the EzCAD board appears under **Laser Mark Control Board** or **Universal Serial Bus controllers** without yellow exclamation marks.
3. **Connect EzCAD USB Hardware Dongle** (if your machine uses an external hardware dongle).

---

## 6. EzCAD Template Configuration (`test.ezd`)

The template defines the text placement, font, size, laser power, marking speed, and frequency:

1. Open **EzCAD 2.14.11** software.
2. Click the **Text** tool on the left toolbar and place a text object on the canvas.
3. In the object property panel on the left:
   * Set **Text Name** to: `t1` *(Exact name `t1` or `T1`)*.
   * Type dummy text (e.g., `000000000000000000000000`).
   * Choose font type (Vector Font, TrueType, Dot Matrix, Barcode, etc.).
   * Set text height, width, and alignment for your tag dimensions.
4. Set the laser pen parameters (e.g., Speed: `1000 mm/s`, Power: `50%`, Frequency: `20 kHz`).
5. Click **File -> Save As...** and save the file as **`test.ezd`**.
6. **CLOSE EZCAD 2.14.11 COMPLETELY**.

> [!WARNING]
> **EzCAD 2.14.11 must NOT be running simultaneously with `RFID_LASER.exe`!**
> EzCAD and `MarkEzd.dll` access the LMC1 USB controller exclusively. If EzCAD is open in the background, the utility will report `Error 1: EZCAD is already running`.

---

## 7. Deploying Application Files to Client PC

1. On your development machine, take the generated deployment folder:
   ```
   D:\AEPL_AUTOMATION\RFID\dist\RFID_LASER\
   ```
2. Copy this entire folder to the client PC (recommended location: `C:\AEPL\RFID_LASER\`).
3. Verify the folder contains the following complete set:
   ```text
   C:\AEPL\RFID_LASER\
   ├── run.bat                <-- One-Click Auto-Launcher (Auto-detects 32/64-bit PC)
   ├── RFID_LASER.exe         <-- Standalone Production Executable (Clean GUI)
   ├── RFID_LASER_debug.exe   <-- Diagnostic Executable (With Live Console)
   ├── MarkEzd.dll            <-- EzCAD Core SDK DLL (32-bit)
   ├── Lmc1.dll               <-- Hardware Board Driver DLL
   ├── DataMgr.dll            <-- Data Management DLL
   ├── mathlib.dll            <-- Geometry Math Library DLL
   ├── LMCMIO.dll             <-- Laser I/O Expansion DLL
   ├── QDib.dll               <-- Image / Bitmap Dependency DLL
   ├── NcPath.dll             <-- Toolpath Dependency DLL
   ├── MFC71.dll              <-- Microsoft Foundation Class Runtime
   ├── Msvcr71.dll            <-- Visual C++ 2003 Runtime DLL
   ├── EZCAD.CFG              <-- EzCAD Hardware & Optics Config
   ├── test.ezd               <-- Laser Template File (contains entity 't1')
   ├── scripts/               <-- Setup & Diagnostic Batch/PS1 Scripts
   │   ├── setup_client.bat
   │   ├── setup_client.ps1
   │   └── diagnose_client.bat
   └── _internal/             <-- Python 3.8 32-bit runtime libraries
   ```

---

## 8. First-Time Software Configuration

1. Double-click `RFID_LASER.exe` (or `RFID_LASER_debug.exe` if debugging).
2. **Serial Connection Setup**:
   * In the **Port** dropdown, select the COM port identified in Step 5 (e.g. `COM6`). Click **⟳** to refresh if needed.
   * Set **Baud** to `115200`.
   * Click **Connect**. The badge will switch to green `CONNECTED`.
3. **Laser Setup**:
   * **Template File**: Verify it points to `C:\AEPL\RFID_LASER\test.ezd` (click **Browse...** if located elsewhere).
   * **EzCAD Path**: Set to `C:\AEPL\RFID_LASER` (the folder containing `MarkEzd.dll`).
   * **Entity Name**: Ensure it is set to `t1`.
   * **Mode**: Ensure **Simulation Mode** is **Unchecked** (`HARDWARE MODE`).
4. Click **✍ Update Template** to verify communication. The log console will display:
   ```
   [SUCCESS] EzCAD [HARDWARE] initialized. Template loaded: test.ezd (Entities: ['t1'])
   ```

---

## 9. Operator Workflow Modes

### Mode A: One-Click Flow (Recommended for Production)
1. Place the RFID tag in the fixture under the laser marking lens.
2. Click **🚀 READ & MARK (AUTO-FLOW)**:
   * Step 1: Utility queries the RFID reader.
   * Step 2: Decoded Tag ID is displayed in the **Tag ID** box.
   * Step 3: Entity `t1` in `test.ezd` is replaced with the Tag ID.
   * Step 4: The laser fires and marks the tag immediately.

### Mode B: Semi-Automated Step-by-Step
1. Click **📡 Read Tag** to read the tag and verify the Tag ID in the input box.
2. (Optional) Edit or verify the Tag ID in the input box.
3. Click **✍ Update Template** to update the text.
4. Click **⚡ Mark Tag** to fire the laser.

### Mode C: High-Throughput Auto-Mark
1. Check the box **Auto-Mark upon receiving Tag ID**.
2. Check the box **Auto-Read Tag** (interval set to e.g. `1.5s` or `2.0s`).
3. Whenever a new tag enters reader range, the utility reads and fires the laser automatically.

---

## 10. Troubleshooting & Error Codes Reference

| Symptom / Error | Cause | Solution |
| :--- | :--- | :--- |
| **`Error 1: EZCAD is already running`** | Standalone EzCAD 2.14.11 GUI application is open. | Close EzCAD 2.14.11 before clicking Connect or Mark. |
| **`Error 3: Failed to open LMC1 control board`** | Laser controller USB is disconnected, laser is unpowered, or driver not installed. | Check USB cable, power switch, and ensure BJJCZ driver is active. The utility will automatically run in Simulation Mode until hardware is connected. |
| **`Error 4: No valid LMC1 device detected`** | Laser controller USB is disconnected or unpowered. | Check USB cable, laser power switch, and Device Manager. |
| **`Error 11: Laser controller not initialized`** | Template loaded before controller initialization. | Resolved in latest release: utility auto-initializes with HWND; check that laser board is connected and uncheck Simulation Mode. |
| **`Error 13: Window handle is null / device absent`** | LMC1 board not initialized or USB dongle absent. | Reconnect laser board USB and restart the utility. |
| **`Error 18: Object not found`** | Entity named `t1` does not exist in `test.ezd`. | Open `test.ezd` in EzCAD, rename the text element to `t1`, save, and close EzCAD. |
| **`Could not open serial port COMx`** | Another software has the port locked. | Close other serial terminals; verify port number in Device Manager. |
| **`No Tag / Empty data response`** | Tag is too far from reader or antenna cable loose. | Adjust tag position over RFID antenna; retry read. |
| **`WinError 126 / 127: DLL load failed`** | Visual C++ runtimes or companion DLLs missing. | Run `scripts\setup_client.bat` to install VC++ x86 runtimes. |
