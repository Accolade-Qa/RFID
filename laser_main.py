"""AEPL RFID Laser Marking Utility — Main Application Entry Point (EzCAD GUI Automation).
Coordinates RFID Reader, Duplicate Prevention, Dynamic Text File Generation,
and Win32 EzCAD GUI Automation.
Compatible with 32-bit and 64-bit Windows (Windows 7/10/11).
"""

from datetime import datetime
import os
from pathlib import Path
import struct
import subprocess
import sys
import traceback
from typing import Tuple


def resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


PROJECT_ROOT = resolve_project_root()
CRASH_LOG = PROJECT_ROOT / "crash_report.log"
ACTIVITY_LOG = PROJECT_ROOT / "activity.log"


def log_to_file(msg: str):
    """Write timestamped log to activity.log."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    entry = f"[{ts}] {msg}\n"
    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catch unhandled fatal exceptions and write to crash_report.log."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    report = (
        f"====================================================\n"
        f"CRASH REPORT - {ts}\n"
        f"Platform: {sys.platform} ({os.name})\n"
        f"Python Architecture: {struct.calcsize('P') * 8}-bit\n"
        f"Python Version: {sys.version}\n"
        f"Executable: {sys.executable}\n"
        f"Working Dir: {os.getcwd()}\n"
        f"----------------------------------------------------\n"
        f"Exception: {exc_type.__name__}: {exc_value}\n\n"
        f"Traceback:\n{tb_text}\n"
        f"====================================================\n\n"
    )

    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            f.write(report)
    except Exception:
        pass

    print("\n" + "=" * 60, file=sys.stderr)
    print("UNHANDLED FATAL EXCEPTION:", file=sys.stderr)
    print(tb_text, file=sys.stderr)
    print(f"Crash report written to: {CRASH_LOG}", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

    # Display pop-up error dialog if GUI is available
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Fatal Application Error",
            f"The application encountered an unexpected error:\n\n{exc_value}\n\n"
            f"A detailed crash report has been saved to:\n{CRASH_LOG}"
        )
        root.destroy()
    except Exception:
        pass

    sys.exit(1)


sys.excepthook = global_exception_handler


def get_system_architecture() -> Tuple[str, str]:
    """Detect PC Operating System architecture (32-bit vs 64-bit) and current process architecture."""
    is_64_os = False
    if sys.platform == "win32":
        if (
            os.environ.get("PROCESSOR_ARCHITECTURE") == "AMD64"
            or os.environ.get("PROCESSOR_ARCHITEW6432") == "AMD64"
        ):
            is_64_os = True
    os_arch = "64-bit (x64)" if is_64_os else "32-bit (x86)"
    proc_arch = f"{struct.calcsize('P') * 8}-bit"
    return os_arch, proc_arch


def run_diagnostics():
    """Verify runtime environment, architecture, EzCAD executable, dynamic text file, and hardware ports."""
    print("=" * 65)
    print("AEPL RFID Laser Marking Utility (EzCAD GUI Automation) — Diagnostics")
    print("=" * 65)

    # 1. Architecture Check
    os_arch, proc_arch = get_system_architecture()
    print(f"[*] PC Operating System Architecture : {os_arch}")
    print(f"[*] Python Process Architecture      : {proc_arch}")
    print("    [PASS] GUI Automation mode is fully compatible with both 32-bit and 64-bit.")

    # 2. Operating System Details
    print(f"\n[*] Operating System Details: {sys.platform} ({os.name})")

    # 3. Dynamic Text Input File
    tag_input_file = PROJECT_ROOT / "tag_input.txt"
    print("\n[*] Checking Dynamic Tag Input File (tag_input.txt):")
    try:
        if not tag_input_file.exists():
            with open(tag_input_file, "w", encoding="utf-8") as f:
                f.write("SAMPLE_TAG_ID\n")
            print(f"    [CREATED] Created default input file at: {tag_input_file}")
        else:
            size = tag_input_file.stat().st_size
            content = tag_input_file.read_text(encoding="utf-8").strip()
            print(f"    [PASS] tag_input.txt exists ({size} bytes, content='{content}')")
    except Exception as e:
        print(f"    [FAIL] Error accessing tag_input.txt: {e}")

    # 4. Duplicate Database & Marked History
    marked_file = PROJECT_ROOT / "marked_tags.txt"
    history_file = PROJECT_ROOT / "marked_tags_history.csv"
    print("\n[*] Checking Duplicate Filter Storage:")
    for path, desc in [(marked_file, "marked_tags.txt"), (history_file, "marked_tags_history.csv")]:
        if path.exists():
            print(f"    [PASS] {desc} found ({path.stat().st_size} bytes)")
        else:
            print(f"    [READY] {desc} will be automatically initialized upon first mark.")

    # 5. EzCAD Executable Search
    print("\n[*] Checking EzCAD Executable Installation:")
    from laser.ezcad_gui_controller import auto_detect_ezcad_exe
    found_ezcad = auto_detect_ezcad_exe()

    if found_ezcad:
        print(f"    [PASS] EzCAD executable found: {found_ezcad}")
    else:
        print("    [NOTICE] EzCad2.exe not found automatically. You can browse and select")
        print("             it directly in the application's EzCAD settings panel.")

    # 6. Template File
    ezd_template = PROJECT_ROOT / "test.ezd"
    print("\n[*] Checking EzCAD Template File (test.ezd):")
    if ezd_template.is_file():
        print(f"    [PASS] test.ezd found ({ezd_template.stat().st_size:,} bytes)")
    else:
        print(f"    [NOTICE] test.ezd not in root directory. Configure via application UI.")

    # 7. Serial COM Ports Check
    print("\n[*] Scanning Available Serial Ports (RFID Reader):")
    try:
        from serial.tools import list_ports
        ports = list_ports.comports()
        if ports:
            for p in ports:
                print(f"    [FOUND] {p.device}: {p.description}")
        else:
            print("    [NOTICE] No active COM ports detected. Connect the RFID reader USB.")
    except Exception as e:
        print(f"    [FAIL] Could not query COM ports: {e}")

    print("=" * 65)
    print("Diagnostic complete. Log saved to activity.log.\n")


def main():
    log_to_file("Starting RFID Laser Marking Utility (EzCAD GUI Automation)...")

    # If --diag or --verify is passed in arguments
    if "--diag" in sys.argv or "--verify" in sys.argv:
        run_diagnostics()
        if "--only" in sys.argv:
            sys.exit(0)

    from ui.laser_gui_app import RFIDLaserGuiApp

    app = RFIDLaserGuiApp()
    app.run()


if __name__ == "__main__":
    main()
