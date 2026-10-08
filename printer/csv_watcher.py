from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RFIDRow:
    timestamp: str
    tag_id: str

    @property
    def key(self) -> str:
        # The reader already de-duplicates tag IDs. Timestamp is included so
        # the persistent state identifies the exact CSV row.
        return f"{self.timestamp}\x1f{self.tag_id}"


class DailyCSV:
    def __init__(self, csv_dir: str | Path, file_prefix: str = "activity_records_"):
        self.csv_dir = Path(csv_dir)
        self.file_prefix = file_prefix

    def current_file(self) -> Path | None:
        # Select the newest matching daily CSV. This avoids requiring the
        # printer to know the date format used by the reader.
        files = sorted(
            self.csv_dir.glob(f"{self.file_prefix}*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return files[0] if files else None

    def read_rows(self, path: Path) -> list[RFIDRow]:
        rows: list[RFIDRow] = []
        if not path.exists():
            return rows

        # utf-8-sig handles a CSV written with a UTF-8 BOM.
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return rows

            required = {"timestamp", "tag_id"}
            if not required.issubset(set(reader.fieldnames)):
                raise ValueError(
                    f"{path} must contain columns: timestamp, tag_id"
                )

            for raw in reader:
                timestamp = (raw.get("timestamp") or "").strip()
                tag_id = (raw.get("tag_id") or "").strip()
                if timestamp and tag_id:
                    rows.append(RFIDRow(timestamp, tag_id))

        return rows
