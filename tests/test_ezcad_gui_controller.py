"""Unit tests for EzcadGuiController."""

import shutil
import tempfile
from pathlib import Path
import pytest

from laser.ezcad_gui_controller import EzcadGuiController


class TestEzcadGuiController:
    @pytest.fixture(autouse=True)
    def setup_tmp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.input_file = Path(self.tmp_dir) / "tag_input.txt"
        yield
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_write_and_read_input_file(self):
        ctrl = EzcadGuiController(input_file_path=str(self.input_file))
        tag = "TAG_XYZ_12345"
        ok, msg = ctrl.write_tag_to_input_file(tag)
        assert ok is True
        assert self.input_file.is_file()

        content = ctrl.read_current_input_file()
        assert content == tag

    def test_simulation_mark(self):
        ctrl = EzcadGuiController(input_file_path=str(self.input_file))
        tag = "SIM_TAG_999"
        ok, msg, duration = ctrl.trigger_mark(tag, mark_delay_sec=0.2, simulation_mode=True)
        assert ok is True
        assert "SIMULATION" in msg
        assert duration >= 0.2
        assert ctrl.read_current_input_file() == tag

    def test_simulation_stop_and_red_light(self):
        ctrl = EzcadGuiController(input_file_path=str(self.input_file))
        ok_stop, msg_stop = ctrl.trigger_stop(simulation_mode=True)
        assert ok_stop is True
        assert "SIMULATION" in msg_stop

        ok_f1, msg_f1 = ctrl.trigger_red_light(simulation_mode=True)
        assert ok_f1 is True
        assert "SIMULATION" in msg_f1
