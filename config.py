import os
import sys
from pathlib import Path

PORT = "COM3"  # Change as needed
BAUDRATE = 115200


def _resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _resolve_app_dir()
LOG_DEFAULT_PATH = str((APP_DIR / "activity.log").resolve())
JSON_DEFAULT_PATH = str((APP_DIR / "activity_records.json").resolve())
CSV_DEFAULT_PATH = str((APP_DIR / "activity_records.csv").resolve())
