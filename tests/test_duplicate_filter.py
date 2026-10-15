"""Unit tests for DuplicateFilter system."""

import shutil
import tempfile
from pathlib import Path
import pytest

from laser.duplicate_filter import DuplicateFilter


class TestDuplicateFilter:
    @pytest.fixture(autouse=True)
    def setup_tmp(self):
        self.tmp_dir = tempfile.mkdtemp()
        yield
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_unique_tag_accepted(self):
        df = DuplicateFilter(self.tmp_dir)
        tag = "TAG1234567890ABCDEF"
        assert df.is_duplicate(tag) is False

        ok, msg = df.check_and_record(tag, duration=1.2)
        assert ok is True
        assert "ACCEPTED" in msg
        assert df.is_duplicate(tag) is True

    def test_duplicate_tag_rejected(self):
        df = DuplicateFilter(self.tmp_dir)
        tag = "TAG_DUPLICATE_001"
        ok1, _ = df.check_and_record(tag)
        assert ok1 is True

        # Second attempt with same tag
        ok2, msg2 = df.check_and_record(tag)
        assert ok2 is False
        assert "DUPLICATE REJECTED" in msg2

        # Case-insensitive duplicate check
        ok3, msg3 = df.check_and_record(tag.lower())
        assert ok3 is False

    def test_statistics_tracking(self):
        df = DuplicateFilter(self.tmp_dir)
        df.check_and_record("TAG_A")
        df.check_and_record("TAG_A")  # Duplicate
        df.check_and_record("TAG_B")
        df.check_and_record("TAG_A")  # Duplicate

        stats = df.get_statistics()
        assert stats["scanned"] == 4
        assert stats["marked"] == 2
        assert stats["duplicates"] == 2

    def test_persistence_across_instances(self):
        df1 = DuplicateFilter(self.tmp_dir)
        df1.check_and_record("TAG_PERSISTENT_999")

        # New instance loading same directory
        df2 = DuplicateFilter(self.tmp_dir)
        assert df2.is_duplicate("TAG_PERSISTENT_999") is True
        assert df2.unique_marked_count == 1

    def test_clear_history(self):
        df = DuplicateFilter(self.tmp_dir)
        df.check_and_record("TAG_TO_CLEAR")
        assert df.is_duplicate("TAG_TO_CLEAR") is True

        df.clear_history()
        assert df.is_duplicate("TAG_TO_CLEAR") is False
        assert df.unique_marked_count == 0
