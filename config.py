import os
import sys
from datetime import datetime
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


def get_daily_csv_path(dt: datetime | None = None) -> str:
    """Returns the daily CSV file path based on the given or current date (YYYY-MM-DD)."""
    if dt is None:
        dt = datetime.now()
    date_str = dt.strftime("%Y-%m-%d")
    return str((APP_DIR / f"activity_records_{date_str}.csv").resolve())


CSV_DEFAULT_PATH = get_daily_csv_path()
