"""Unit tests for PC architecture detection (32-bit vs 64-bit)."""

import struct
from laser_main import get_system_architecture


def test_get_system_architecture():
    os_arch, proc_arch = get_system_architecture()
    assert os_arch in ["64-bit (x64)", "32-bit (x86)"]
    assert proc_arch in ["32-bit", "64-bit"]
    expected_proc = f"{struct.calcsize('P') * 8}-bit"
    assert proc_arch == expected_proc
