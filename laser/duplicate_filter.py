"""Persistent Duplicate Tag ID Filter and Tracking System.
Ensures no duplicate RFID tag ID is marked more than once.
"""

from datetime import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DuplicateFilter:
    """Manages history of marked tags, rejecting duplicates across sessions."""

    def __init__(self, history_dir: Optional[str] = None):
        self.history_dir = Path(history_dir).resolve() if history_dir else Path.cwd()
        self.tags_file = self.history_dir / "marked_tags.txt"
        self.csv_file = self.history_dir / "marked_tags_history.csv"

        self.marked_set: Set[str] = set()
        self.history_records: List[Dict[str, str]] = []

        self.total_scanned_count: int = 0
        self.unique_marked_count: int = 0
        self.duplicates_blocked_count: int = 0

        self.load_history()

    def _normalize(self, tag_id: str) -> str:
        """Strip whitespace and normalize to uppercase."""
        return tag_id.strip().upper()

    def load_history(self) -> int:
        """Load previously marked tags from disk so protection survives restarts."""
        self.marked_set.clear()
        self.history_records.clear()

        if self.tags_file.is_file():
            try:
                with open(self.tags_file, "r", encoding="utf-8") as f:
                    for line in f:
                        clean = self._normalize(line)
                        if clean and not clean.startswith("#"):
                            self.marked_set.add(clean)
            except Exception:
                pass

        if self.csv_file.is_file():
            try:
                with open(self.csv_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) >= 2 and parts[0] != "Timestamp":
                            self.history_records.append({
                                "timestamp": parts[0],
                                "tag_id": parts[1].strip().upper(),
                                "duration": parts[2] if len(parts) > 2 else "0.00",
                            })
            except Exception:
                pass

        self.unique_marked_count = len(self.marked_set)
        return len(self.marked_set)

    def is_duplicate(self, tag_id: str) -> bool:
        """Check if a Tag ID has already been marked."""
        clean = self._normalize(tag_id)
        if not clean:
            return False
        return clean in self.marked_set

    def check_and_record(self, tag_id: str, duration: float = 0.0) -> Tuple[bool, str]:
        """Check if tag is unique. If unique, record it and return (True, msg).
        If duplicate, return (False, warning_msg).
        """
        clean = self._normalize(tag_id)
        self.total_scanned_count += 1

        if not clean:
            return False, "Empty Tag ID received."

        if clean in self.marked_set:
            self.duplicates_blocked_count += 1
            return False, f"DUPLICATE REJECTED: Tag '{clean}' has already been marked!"

        # Tag is new and unique -> Record it
        self.marked_set.add(clean)
        self.unique_marked_count += 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Append to marked_tags.txt
        try:
            with open(self.tags_file, "a", encoding="utf-8") as f:
                f.write(f"{clean}\n")
        except Exception:
            pass

        # 2. Append to marked_tags_history.csv
        try:
            write_header = not self.csv_file.is_file()
            with open(self.csv_file, "a", encoding="utf-8") as f:
                if write_header:
                    f.write("Timestamp,Tag_ID,Duration_Sec\n")
                f.write(f"{now_str},{clean},{duration:.2f}\n")
        except Exception:
            pass

        self.history_records.append({
            "timestamp": now_str,
            "tag_id": clean,
            "duration": f"{duration:.2f}",
        })

        return True, f"UNIQUE TAG ACCEPTED: Tag '{clean}' registered successfully."

    def clear_history(self) -> None:
        """Clear the history (used when starting a completely new production lot)."""
        self.marked_set.clear()
        self.history_records.clear()
        self.total_scanned_count = 0
        self.unique_marked_count = 0
        self.duplicates_blocked_count = 0

        # Backup old file and start fresh
        try:
            if self.tags_file.is_file():
                bak = self.history_dir / f"marked_tags_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                self.tags_file.rename(bak)
            if self.csv_file.is_file():
                bak_csv = self.history_dir / f"marked_tags_history_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                self.csv_file.rename(bak_csv)
        except Exception:
            pass

    def get_statistics(self) -> Dict[str, int]:
        """Return live counts for UI display."""
        return {
            "scanned": self.total_scanned_count,
            "marked": self.unique_marked_count,
            "duplicates": self.duplicates_blocked_count,
        }

    def get_recent_history(self, max_items: int = 50) -> List[Dict[str, str]]:
        """Return the most recent marked tags."""
        return self.history_records[-max_items:]
