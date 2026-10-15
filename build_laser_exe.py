"""Build script to compile RFID_LASER into standalone 32-bit Windows executables.
Builds both:
- RFID_LASER.exe (Production GUI - windowed without console)
- RFID_LASER_debug.exe (Diagnostic GUI - with live terminal console for tracking errors & frames)
"""

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    app_dir = Path(__file__).resolve().parent
    dist_dir = app_dir / "dist"
    build_dir = app_dir / "build"
    out_dir = dist_dir / "RFID_LASER"

    print("==========================================================")
    print("Building RFID Laser Marking Utilities (32-bit Windows 7)")
    print("==========================================================")

    # Clean previous build artifacts
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # 1. Build Production Windowed Executable (RFID_LASER.exe)
    print("\n[STEP 1/2] Compiling Production Executable (RFID_LASER.exe)...")
    cmd_prod = [
        "py",
        "-3.8-32",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--hidden-import=serial",
        "--hidden-import=serial.tools.list_ports",
        "--hidden-import=pyautogui",
        "--hidden-import=pygetwindow",
        "--hidden-import=communication.protocol",
        "--hidden-import=communication.uart",
        "--hidden-import=laser.duplicate_filter",
        "--hidden-import=laser.ezcad_gui_controller",
        "--hidden-import=ui.laser_gui_app",
        "--name=RFID_LASER",
        str(app_dir / "laser_main.py"),
    ]
    res_prod = subprocess.run(cmd_prod, cwd=str(app_dir))
    if res_prod.returncode != 0:
        print("[ERROR] Production build failed!")
        sys.exit(res_prod.returncode)

    # 2. Build Debug / Diagnostic Executable with Console (RFID_LASER_debug.exe)
    print("\n[STEP 2/2] Compiling Diagnostic Executable (RFID_LASER_debug.exe with live console)...")
    cmd_debug = [
        "py",
        "-3.8-32",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--console",
        "--hidden-import=serial",
        "--hidden-import=serial.tools.list_ports",
        "--hidden-import=pyautogui",
        "--hidden-import=pygetwindow",
        "--hidden-import=communication.protocol",
        "--hidden-import=communication.uart",
        "--hidden-import=laser.duplicate_filter",
        "--hidden-import=laser.ezcad_gui_controller",
        "--hidden-import=ui.laser_gui_app",
        "--name=RFID_LASER_debug",
        str(app_dir / "laser_main.py"),
    ]
    res_debug = subprocess.run(cmd_debug, cwd=str(app_dir))
    if res_debug.returncode != 0:
        print("[ERROR] Debug build failed!")
        sys.exit(res_debug.returncode)

    # Merge RFID_LASER_debug.exe into dist/RFID_LASER folder
    debug_exe = dist_dir / "RFID_LASER_debug" / "RFID_LASER_debug.exe"
    if debug_exe.is_file() and out_dir.exists():
        shutil.copy2(debug_exe, out_dir / "RFID_LASER_debug.exe")
        print("Merged RFID_LASER_debug.exe into dist/RFID_LASER/")

    # 3. Copy templates, dynamic input file, scripts, and deployment guide
    print("\n[STEP 3/3] Bundling template, dynamic input file, client scripts, and deployment guide...")
    for fname in ["test.ezd", "tag_input.txt", "deployment.md"]:
        src = app_dir / fname
        if src.is_file():
            shutil.copy2(src, out_dir / fname)
            print(f"  + Bundled File: {fname}")

    # Copy setup & diagnostic scripts
    scripts_src = app_dir / "scripts"
    scripts_dst = out_dir / "scripts"
    if scripts_src.is_dir():
        if scripts_dst.exists():
            shutil.rmtree(scripts_dst)
        shutil.copytree(scripts_src, scripts_dst)
        print("  + Bundled client scripts/ directory")

    # Copy auto-launcher run.bat
    run_bat = app_dir / "run.bat"
    if run_bat.is_file():
        shutil.copy2(run_bat, out_dir / "run.bat")
        print("  + Bundled auto-launcher: run.bat")

    print("\n==========================================================")
    print("[SUCCESS] Build Complete! Package ready in:")
    print(f"  -> {out_dir}")
    print("Files created:")
    print(f"  1. Production:  {out_dir / 'RFID_LASER.exe'} (Clean GUI)")
    print(f"  2. Diagnostic:  {out_dir / 'RFID_LASER_debug.exe'} (With Live Console)")
    print(f"  3. Client Setup:{out_dir / 'scripts' / 'setup_client.bat'}")
    print("==========================================================")


if __name__ == "__main__":
    build()
