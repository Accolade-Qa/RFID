"""Build script to compile RFID_LASER into a standalone 32-bit Windows executable."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def build():
    app_dir = Path(__file__).resolve().parent
    dist_dir = app_dir / "dist"
    build_dir = app_dir / "build"

    print("==================================================")
    print("Building RFID Laser Marking Utility (32-bit Win7)")
    print("==================================================")

    # Clean previous build artifacts
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    cmd = [
        "py",
        "-3.8-32",
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name=RFID_LASER",
        "--add-data=test.ezd;.",
        "--add-data=EZCAD.CFG;.",
        "--add-data=MarkEzd.dll;.",
        "--add-data=Lmc1.dll;.",
        "--add-data=DataMgr.dll;.",
        "--add-data=mathlib.dll;.",
        "--add-data=LMCMIO.dll;.",
        str(app_dir / "laser_main.py"),
    ]

    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(app_dir))

    if result.returncode != 0:
        print("[ERROR] Build failed!")
        sys.exit(result.returncode)

    # Copy DLLs and templates into dist/RFID_LASER output folder
    out_dir = dist_dir / "RFID_LASER"
    if out_dir.exists():
        files_to_copy = [
            "DataMgr.dll",
            "EZCAD.CFG",
            "Lmc1.dll",
            "LMCMIO.dll",
            "MarkEzd.dll",
            "mathlib.dll",
            "test.ezd",
        ]
        for fname in files_to_copy:
            src = app_dir / fname
            dst = out_dir / fname
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                print(f"Copied companion file: {fname} -> dist/RFID_LASER")

    print("\n[SUCCESS] Build completed successfully!")
    print(f"Executable directory: {out_dir}")
    print(f"Executable path: {out_dir / 'RFID_LASER.exe'}")


if __name__ == "__main__":
    build()
