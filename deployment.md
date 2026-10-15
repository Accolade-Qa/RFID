# AEPL RFID Laser Marking System — EzCAD GUI Automation Deployment Guide

This guide details the deployment, configuration, and operation of the **AEPL RFID Laser Marking System (EzCAD GUI Automation Mode)**.

---

## 1. Architecture Overview

### Why EzCAD GUI Automation?
In production environments, JCZ EzCAD hardware controllers (`LMC1` boards) frequently use hardware dongles or vendor-locked firmware (`JczDog.dll`, `MarkEzd.dll`) that reject direct third-party SDK calls with `LMC1_ERR_NOINITIAL` or vendor authorization errors.

The **EzCAD GUI Automation** mode provides a 100% reliable, zero-dongle-restriction solution by leveraging the licensed, standalone EzCAD program (`EzCad2.exe` / `Ezcad.exe`):
1. **Dynamic File Linkage**: EzCAD is configured with a **Variable Text** object reading directly from `tag_input.txt`.
2. **PyAutoGUI & Win32 Automation**: When an RFID tag is scanned, Python writes the Tag ID to `tag_input.txt`, focuses the EzCAD window, and triggers the hardware mark hotkey (**F2**) using PyAutoGUI with Win32 fallback. EzCAD is automatically located on the system if placed in Downloads, Desktop, or standard paths.
3. **Hardware Wait**: Python coordinates marking duration and pauses until laser completion before accepting the next tag.
4. **Duplicate Prevention**: Every scanned Tag ID is checked against an in-memory set and persistent database (`marked_tags.txt` & `marked_tags_history.csv`). Duplicate tags are blocked with an immediate visual warning and never re-marked.

```
┌─────────────────┐       COM Port        ┌──────────────────────────────┐
│ RFID USB Reader │ ────────────────────> │  AEPL RFID Controller App    │
└─────────────────┘  (115200 baud, 8N1)   │  (laser_main.py / .exe)      │
                                          └──────────────┬───────────────┘
                                                         │
                                        1. Check Duplicate Filter
                                        2. Write Tag ID to tag_input.txt
                                        3. Focus EzCad2.exe & Send F2
                                                         │
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │     EzCad2.exe (Licensed)    │
                                          │  - Variable Text -> File     │
                                          │  - Laser Hardware Controller │
                                          └──────────────┬───────────────┘
                                                         │
                                                  USB LMC1 Board
                                                         ▼
                                          ┌──────────────────────────────┐
                                          │      Fiber Laser Marker      │
                                          └──────────────────────────────┘
```

---

## 2. System Prerequisites & Architecture Compatibility

The application is engineered to run seamlessly across all modern and legacy Windows client PCs:

| Component | 32-bit Systems (x86) | 64-bit Systems (x64) |
| :--- | :--- | :--- |
| **Operating System** | Windows 7 SP1, Windows 8, Windows 10, Windows 11 | Windows 7 SP1, Windows 8, Windows 10, Windows 11 |
| **Execution Subsystem**| Native 32-bit Win32 | WOW64 Subsystem (built-in Windows 64-bit) |
| **Standalone Binaries**| `RFID_LASER.exe` & `RFID_LASER_debug.exe` | Same executables run natively via WOW64 |
| **Python Support** | Python 3.8+ (32-bit) | Python 3.8+ (32-bit or 64-bit) |
| **EzCAD Version** | EzCAD 2.14.x / 2.7.x / 2.9.x | EzCAD 2.14.x / 2.7.x / 2.9.x |
| **RFID Reader Drivers**| Prolific PL2303 / FTDI / CH340 USB-Serial Driver | Prolific PL2303 / FTDI / CH340 USB-Serial Driver |

---

## 3. EzCAD Software Setup (Variable Text Configuration)

EzCAD must be configured once to link its marking text entity to `tag_input.txt`. Follow these exact steps:

### Step 3.1: Open EzCAD & Load Template
1. Launch **EzCad2.exe**.
2. Open your template file (e.g., `test.ezd`) or create a new document (`Ctrl + N`).

### Step 3.2: Create or Select the Text Entity
1. Click the **Text (F)** tool from the left toolbar, and click on the canvas to place a text object.
2. Set your desired font, font size, and laser hatch settings in the left properties panel.

### Step 3.3: Enable Variable Text
1. In the left Text Properties panel, locate the **"Variable Text"** (or **"Vary Text"**) checkbox.
2. Check the box **[x] Enable Variable Text**.
3. A list view labeled **"Variable Text List"** will activate below the checkbox.

### Step 3.4: Add Dynamic File Input
1. Click the **"Add"** (or **"+"**) button next to the variable text list.
2. In the dialog that appears, select the source type:
   - Select **"File"** (or **"From File"**).
3. Set the File Properties:
   - **File Type**: Select **Text (*.txt)**.
   - **File Name**: Click **"Browse"** and select `tag_input.txt` from your application directory (e.g., `D:\AEPL_AUTOMATION\RFID\tag_input.txt` or `C:\AEPL\RFID\tag_input.txt`).
   - **Read Mode**: Set to **Line 1** (or First Line).
   - **Auto update**: Enabled / Read on Mark.
4. Click **OK** to confirm.

### Step 3.5: Save Template
1. Press `Ctrl + S` and save the template as `test.ezd` in your application folder.
2. EzCAD is now ready to receive dynamic Tag IDs from the python automation app!

---

## 4. Hardware Wiring & Connectivity

1. **RFID Reader**:
   - Connect the RFID USB Reader to any USB port on the client PC.
   - Open Windows **Device Manager** -> **Ports (COM & LPT)** to note the assigned COM port (e.g., `COM3`, `COM6`).
2. **EzCAD Laser Marker**:
   - Ensure the EzCAD USB cable is securely connected to the PC.
   - Power on the laser DC power supply, fiber laser source, and exhaust/chiller.
   - Verify that EzCAD shows status: **"Laser Ready"** (no "LMC1 board not found" demo mode).

---

## 5. Running the Application

### Option A: Standalone Executable (Recommended for Client PC)
Navigate to the application folder and double-click:
- **`RFID_LASER.exe`**: Clean production graphical user interface (no console window).
- **`RFID_LASER_debug.exe`**: Diagnostic version with a live terminal console showing raw serial hex frames, Win32 hotkey triggers, and duplicate filter checks.
- **`run.bat`**: Universal launcher that automatically detects PC architecture and launches the best executable.

### Option B: Running via Python
If running from source code on the client machine:
```cmd
:: Quick diagnostic verification
python laser_main.py --diag --only

:: Launch application
python laser_main.py
```

---

## 6. Application Configuration & Operation Walkthrough

### 6.1 Connect RFID Reader
1. In the **RFID Reader Connection** panel at the top:
   - Select the detected COM Port from the dropdown (e.g., `COM6`).
   - Baud Rate: Default is `115200`.
   - Click **"Connect"**.
   - The status badge will switch to **🟢 Connected: COMx (115200)**.

### 6.2 EzCAD Settings Panel
1. **EzCAD Executable**: Browse and select `EzCad2.exe`.
2. **Template File**: Browse and select `test.ezd`.
3. **Dynamic Input File**: Path to `tag_input.txt` (auto-detected).
4. **Mark Duration (s)**: Adjust slider to match your laser's cycle time (e.g., `1.5` - `3.0` seconds).
5. Click **"Launch / Focus EzCAD"**: Verifies that the app successfully detects and restores the EzCAD window.
6. Click **"Red Light (F1)"**: Sends F1 to EzCAD to preview laser positioning.

### 6.3 Duplicate Prevention System
The duplicate prevention system guarantees that no RFID tag is marked more than once:
- **[x] Enforce Strict Duplicate Prevention**: Checked by default.
- When an RFID tag is scanned:
  - If **Unique**: A green banner **"🟢 UNIQUE TAG: Ready to mark"** appears.
  - If **Duplicate**: An amber banner **"🟡 DUPLICATE TAG: Blocked! Already marked"** appears, and the laser fire command is strictly prevented.
- **Marked History**: Click **"View History"** to inspect all previously marked tags with timestamps and durations.
- **Clear History**: Click **"Clear History"** if a new production batch requires resetting the marked tag database (previous data is safely archived with timestamp).

### 6.4 Marking Workflow
#### Manual Single-Tag Mark:
1. Scan an RFID tag (or click "Auto-Read Tag").
2. Verify the 24-character hexadecimal Tag ID appears.
3. Click **"Update Text File"** to update `tag_input.txt`.
4. Click **"Mark Tag (F2)"**: Python brings EzCAD to the foreground, issues F2, and displays live feedback **"⏳ MARKING IN PROGRESS"** until the mark duration elapses.

#### Fully Automated Continuous Pipeline:
1. Toggle **"Auto Read & Mark (Continuous Pipeline)"** to **ON**.
2. Pass workpieces under the RFID reader.
3. The application automatically:
   - Reads the tag frame (`24 11 01 00 8B FE 23`).
   - Checks the duplicate filter.
   - If unique, writes `tag_input.txt` and fires the laser via F2.
   - Displays **"✅ MARK COMPLETE: Waiting for next tag"**.
   - If a duplicate tag is scanned, skips marking and logs the duplicate event.

---

## 7. Troubleshooting & FAQs

### Q1: EzCAD window is minimized or behind other windows. Will F2 still work?
**Yes.** The application uses Win32 API calls (`ShowWindow(SW_RESTORE)`, `AttachThreadInput`, and `SetForegroundWindow`) to bring EzCAD to the front before sending keypresses.

### Q2: How can I stop the laser immediately in an emergency?
Click the big red **"STOP (ESC)"** button in the application, or press the physical laser emergency stop switch.

### Q3: How do I verify all components before production?
Run the diagnostic check:
```cmd
RFID_LASER_debug.exe --diag --only
```
The console will verify:
- PC architecture and Windows version
- `tag_input.txt` read/write permissions
- `marked_tags.txt` database integrity
- EzCAD installation path
- Serial COM port availability

### Q4: Where are logs and history stored?
- Application logs: `activity.log`
- Crash reports (if any error occurs): `crash_report.log`
- Current marked tags database: `marked_tags.txt`
- Detailed CSV history with timestamps: `marked_tags_history.csv`
- UI preferences: `laser_gui_settings.json`
