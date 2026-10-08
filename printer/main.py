from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from csv_watcher import DailyCSV
from ezcad import EZCAD, EZCADError
from state import StateStore


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Create {CONFIG_FILE} from config.example.json first."
        )
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def configure_logging(log_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def run() -> None:
    cfg = load_config()
    configure_logging(BASE_DIR / "printer.log")
    log = logging.getLogger("printer")

    ezcad_dir = Path(cfg["ezcad_dir"])
    dll_path = Path(cfg.get("markezd_dll", ezcad_dir / "MarkEzd.dll"))
    template = Path(cfg["template_ezd"])
    csv_dir = Path(cfg["csv_dir"])
    state_path = Path(cfg.get("state_file", BASE_DIR / "printer_state.json"))
    object_name = cfg["text_object_name"]
    poll_seconds = float(cfg.get("poll_seconds", 1.0))
    test_mode = bool(cfg.get("test_mode", False))
    fly_mark = bool(cfg.get("fly_mark", False))

    csv_reader = DailyCSV(
        csv_dir=csv_dir,
        file_prefix=cfg.get("csv_file_prefix", "activity_records_"),
    )
    state = StateStore(state_path)

    log.info("Starting RFID -> EZCAD printer")
    log.info("EZCAD directory: %s", ezcad_dir)
    log.info("Template: %s", template)
    log.info("CSV directory: %s", csv_dir)
    log.info("Text object: %s", object_name)

    ezcad = EZCAD(dll_path)

    try:
        ezcad.initial(ezcad_dir, test_mode=test_mode)
        log.info("LMC1 initialized")

        # Load the template once. Each marking operation modifies the named
        # text object in the in-memory EZCAD database.
        ezcad.load_template(template)
        log.info("EZD template loaded")

        while True:
            csv_file = csv_reader.current_file()
            if csv_file is None:
                time.sleep(poll_seconds)
                continue

            try:
                rows = csv_reader.read_rows(csv_file)
            except Exception:
                log.exception("Unable to read CSV: %s", csv_file)
                time.sleep(poll_seconds)
                continue

            # Rows are naturally FIFO because the CSV reader preserves file order.
            # We process exactly one row, wait for lmc1_Mark() to return, persist
            # success, and only then move to the next row.
            next_row = next(
                (row for row in rows if not state.contains(row.key)),
                None,
            )

            if next_row is None:
                time.sleep(poll_seconds)
                continue

            log.info(
                "Pending RFID: %s | timestamp=%s | file=%s",
                next_row.tag_id,
                next_row.timestamp,
                csv_file.name,
            )

            try:
                ezcad.change_text(object_name, next_row.tag_id)
                log.info("Text updated: %s", next_row.tag_id)

                ezcad.mark(fly_mark=fly_mark)
                log.info("Mark completed: %s", next_row.tag_id)

                # Only mark the CSV row as processed after the DLL reports
                # successful completion.
                state.add(next_row.key)
                log.info("State committed: %s", next_row.tag_id)

            except EZCADError:
                log.exception(
                    "EZCAD operation failed for RFID %s. "
                    "The row remains pending and will be retried.",
                    next_row.tag_id,
                )
                time.sleep(poll_seconds)

            except Exception:
                log.exception(
                    "Unexpected failure for RFID %s. "
                    "The row remains pending and will be retried.",
                    next_row.tag_id,
                )
                time.sleep(poll_seconds)

    finally:
        try:
            ezcad.close()
        except Exception:
            log.exception("Error while closing EZCAD")
        log.info("Printer stopped")


if __name__ == "__main__":
    run()
