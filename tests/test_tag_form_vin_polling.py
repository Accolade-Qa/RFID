import os
import tempfile
import unittest

from config import LOG_DEFAULT_PATH
from logger.log_console import LogConsole


class TestActivityLogging(unittest.TestCase):
    def test_default_log_path_is_relative_to_app_directory_and_auto_save_is_enabled(self):
        self.assertTrue(os.path.isabs(LOG_DEFAULT_PATH))
        self.assertTrue(LOG_DEFAULT_PATH.lower().endswith("activity.log"))

        log_console = LogConsole()
        self.assertTrue(log_console.auto_save)
        self.assertEqual(log_console.file_path, LOG_DEFAULT_PATH)

    def test_appends_are_written_to_disk_when_auto_save_is_on(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "activity.log")

            log_console = LogConsole()
            log_console.set_file_path(log_path)
            log_console.enable_auto_save(True)
            log_console.append("user activity saved automatically")

            with open(log_path, "r", encoding="utf-8") as handle:
                saved = handle.read()

            self.assertIn("user activity saved automatically", saved)


if __name__ == "__main__":
    unittest.main()
