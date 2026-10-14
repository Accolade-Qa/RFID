# AEPL RFID Laser Marking Utility — Deployment & Client Configuration Guide

This guide provides end-to-end instructions for deploying, configuring, and operating the **AEPL RFID Laser Marking Utility** on client PCs running **Windows 7 (32-bit / 64-bit)** with **EzCAD 2.14.11**.

---

## 📋 Table of Contents
1. [How It Works (System Architecture)](#1-how-it-works-system-architecture)
2. [Client PC System Prerequisites](#2-client-pc-system-prerequisites)
3. [Step 1: Hardware Connections & Device Drivers](#step-1-hardware-connections--device-drivers)
4. [Step 2: EzCAD Template Configuration (`test.ezd`)](#step-2-ezcad-template-configuration-testezd)
5. [Step 3: Deploying Application Files to Client PC](#step-3-deploying-application-files-to-client-pc)
6. [Step 4: First-Time Software Configuration](#step-4-first-time-software-configuration)
7. [Step 5: Operator Workflow Modes](#step-5-operator-workflow-modes)
8. [Troubleshooting & Error Codes](#troubleshooting--error-codes)

---

## 1. How It Works (System Architecture)

```
┌─────────────────┐       UART (COM Port)       ┌──────────────────────────────┐
│   RFID Reader   │ ◄─────────────────────────► │  RFID Laser Marking Utility  │
│   (AEPL VLTD)   │   24 11 01 00 8B FE 23      │       (RFID_LASER.exe)       │
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

## 2. Client PC System Prerequisites

| Item | Requirement | Notes |
| :--- | :--- | :--- |
| **Operating System** | **Windows 7 SP1 (32-bit)** *(64-bit also supported)* | Ensure KB2533623 / Service Pack 1 is installed. |
| **Laser Controller** | BJJCZ LMC1 / EzCAD 2.14.11 USB board | USB board driver must be installed and active. |
| **RFID Reader** | AEPL Serial / USB-UART Reader | Silicon Labs CP210x, FTDI, or CH340 USB-UART. |
| **Visual C++ Runtimes** | **Visual C++ 2010 & 2015–2022 (x86 / 32-bit)** | Required by Python 3.8 and EzCAD DLLs. |
| **Python** | **Not Required** on client PC | The application is pre-compiled as a standalone executable. |

> [!IMPORTANT]
> Always install **32-bit (x86)** Visual C++ redistributable runtimes on the client machine, even if the client OS is 64-bit, because EzCAD 2.14.11 and `MarkEzd.dll` are 32-bit binaries.

---

## Step 1: Hardware Connections & Device Drivers

1. **Connect RFID Reader**:
   * Plug the RFID reader's USB cable into the PC.
   * Open **Device Manager** (`devmgmt.msc`) -> expand **Ports (COM & LPT)**.
   * Note the allocated port number (e.g. `COM3` or `COM4`).
2. **Connect Laser Controller (LMC1)**:
   * Plug the EzCAD USB controller cable into the PC and turn on the laser controller power supply.
   * In **Device Manager**, verify that the EzCAD board appears under **Laser Mark Control Board** or **Universal Serial Bus controllers** without yellow exclamation marks.
3. **Connect EzCAD USB Hardware Dongle** (if your version uses a separate USB security dongle).

---

## Step 2: EzCAD Template Configuration (`test.ezd`)

The template defines the position, font size, laser power, marking speed, and frequency:

1. Open **EzCAD 2.14.11** software.
2. Click the **Text** tool on the left toolbar and click on the workspace to place a text object.
3. In the object property panel on the left:
   * Set **Text Name** to: `t1` *(Exact name `t1` or `T1`)*.
   * Type any dummy text (e.g., `000000000000000000000000`).
   * Choose font type (e.g., Vector Font, TrueType, Dot Matrix, Barcode, etc.).
   * Set text height, width, and alignment as needed for the tag size.
4. Set the laser pen parameters (Speed: e.g. `1000 mm/s`, Power: e.g. `50%`, Frequency: e.g. `20 kHz`).
5. Click **File -> Save As...** and save the file as **`test.ezd`**.
6. **CLOSE EZCAD 2.14.11 COMPLETELY**.

> [!WARNING]
> **EzCAD 2.14.11 must NOT be running simultaneously with `RFID_LASER.exe`!**
> EzCAD and `MarkEzd.dll` access the LMC1 USB controller exclusively. If EzCAD is open in the background, the utility will report `Error 1: EZCAD is already running`.

---

## Step 3: Deploying Application Files to Client PC

1. On your development machine, take the generated deployment folder:
   ```
   D:\AEPL_AUTOMATION\RFID\dist\RFID_LASER\
   ```
2. Copy this entire folder to the client PC (recommended location: `C:\AEPL\RFID_LASER\`).
3. Verify the folder contains the following essential files:
   ```text
   C:\AEPL\RFID_LASER\
   ├── RFID_LASER.exe         <-- Standalone Application Executable
   ├── MarkEzd.dll            <-- EzCAD SDK Core DLL (32-bit)
   ├── Lmc1.dll               <-- Hardware Board Driver DLL
   ├── DataMgr.dll            <-- Data Management DLL
   ├── mathlib.dll            <-- Geometry Math Library DLL
   ├── LMCMIO.dll             <-- Laser I/O Expansion DLL
   ├── EZCAD.CFG              <-- EzCAD Hardware & Optics Config
   ├── test.ezd               <-- Laser Template File (contains entity 't1')
   └── _internal/             <-- Python 3.8 32-bit runtime libraries
   ```
4. Right-click `RFID_LASER.exe` -> **Send to -> Desktop (create shortcut)**.

---

## Step 4: First-Time Software Configuration

1. Double-click `RFID_LASER.exe` to launch the utility.
2. **Serial Connection Setup**:
   * In the **Port** dropdown, select the COM port identified in Step 1 (e.g. `COM3`). If not shown, click **⟳** to refresh.
   * Set **Baud** to `115200` (standard for AEPL RFID readers).
   * Click **Connect**. The badge will switch from `DISCONNECTED` to green `CONNECTED`.
3. **Laser Setup**:
   * **Template File**: Verify it points to `C:\AEPL\RFID_LASER\test.ezd` (click **Browse...** if located elsewhere).
   * **EzCAD Path**: Set to `C:\AEPL\RFID_LASER` (the folder containing `MarkEzd.dll`).
   * **Entity Name**: Ensure it is set to `t1`.
   * **Mode**: Ensure **Simulation Mode** is **Unchecked** (the top badge will display `HARDWARE MODE`).
4. Click **✍ Update Template** to test that the template loads and entity `t1` is recognized. The log window will display:
   ```
   [SUCCESS] EzCAD [HARDWARE] initialized. Template loaded: test.ezd (Entities: ['t1'])
   ```

---

## Step 5: Operator Workflow Modes

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

## Troubleshooting & Error Codes

| Symptom / Error | Cause | Solution |
| :--- | :--- | :--- |
| **`Error 1: EZCAD is already running`** | Standalone EzCAD 2.14.11 GUI application is open. | Close EzCAD 2.14.11 before clicking Connect or Mark. |
| **`Error 4: No valid LMC1 device detected`** | Laser controller USB is disconnected or unpowered. | Check USB cable, laser power switch, and Device Manager. |
| **`Error 13: Window handle is null / device absent`** | LMC1 board not initialized or USB dongle absent. | Reconnect laser board USB and restart the utility. |
| **`Error 18: Object not found`** | Entity named `t1` does not exist in `test.ezd`. | Open `test.ezd` in EzCAD, rename the text element to `t1`, save, and close EzCAD. |
| **`Could not open serial port COMx`** | Another software (e.g. PuTTY, previous app) has the port locked. | Close other serial terminals; verify port number in Device Manager. |
| **`No Tag / Empty data response`** | Tag is too far from reader or antenna cable loose. | Adjust tag position over RFID antenna; retry read. |
| **`WinError 126 / 127: DLL load failed`** | Companion DLLs (`DataMgr.dll`, `Lmc1.dll`, etc.) missing. | Ensure all 6 DLLs and `EZCAD.CFG` remain in the same folder as `RFID_LASER.exe`. |
