"""EZCAD 2.14.11 Laser Marking Driver via MarkEzd.dll ctypes integration."""

import ctypes
import os
import struct
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

from laser.errors import EZCADError, EZCAD_ERROR_MESSAGES


class BaseLaserDriver:
    """Base interface for laser drivers."""

    is_simulation: bool = False
    fallback_reason: Optional[str] = None

    def initialize(self, ezcad_dir: Optional[str] = None, test_mode: bool = False, hwnd: Optional[int] = None) -> None:
        raise NotImplementedError

    def load_template(self, ezd_path: str) -> None:
        raise NotImplementedError

    def list_entities(self) -> List[str]:
        raise NotImplementedError

    def change_text(self, entity_name: str, new_text: str) -> Tuple[bool, str]:
        raise NotImplementedError

    def mark(self, fly_mark: bool = False) -> Tuple[bool, str]:
        raise NotImplementedError

    def stop_mark(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def is_initialized(self) -> bool:
        raise NotImplementedError

    def get_last_mark_duration(self) -> float:
        return getattr(self, "last_mark_duration", 0.0)



class HardwareEzcadDriver(BaseLaserDriver):
    """Direct 32-bit ctypes wrapper for MarkEzd.dll."""

    def __init__(self, ezcad_dir: str):
        self.ezcad_dir = str(Path(ezcad_dir).resolve())
        self.dll_path = os.path.join(self.ezcad_dir, "MarkEzd.dll")
        self.initialized = False
        self.is_simulation = False
        self.fallback_reason = None
        self.loaded_template: Optional[str] = None
        self._entities: List[str] = []
        self.last_mark_duration: float = 0.0

        # Enforce 32-bit architecture
        if struct.calcsize("P") * 8 != 32:
            raise RuntimeError(
                f"MarkEzd.dll is a 32-bit binary. Current Python is {struct.calcsize('P') * 8}-bit. "
                "Please run with 32-bit Python 3.8."
            )

        if not os.path.isfile(self.dll_path):
            raise FileNotFoundError(f"MarkEzd.dll not found in {self.ezcad_dir}")

        # Register DLL search directory
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(self.ezcad_dir)
            except Exception:
                pass
        try:
            ctypes.windll.kernel32.SetDllDirectoryW(self.ezcad_dir)
        except Exception:
            pass

        # Load DLL
        try:
            self.dll = ctypes.WinDLL(self.dll_path)
        except Exception as exc:
            raise EZCADError(11, "Load MarkEzd.dll", str(exc))

        self._bind_functions()

    def _bind_functions(self) -> None:
        def _bind(name, argtypes, restype=ctypes.c_int):
            if hasattr(self.dll, name):
                fn = getattr(self.dll, name)
                fn.argtypes = argtypes
                fn.restype = restype
                return fn
            return None

        self._lmc1_Initial2 = _bind("lmc1_Initial2", [ctypes.c_wchar_p, ctypes.c_int])
        self._lmc1_Initial = _bind("lmc1_Initial", [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p])
        self._lmc1_Close = _bind("lmc1_Close", [])
        self._lmc1_LoadEzdFile = _bind("lmc1_LoadEzdFile", [ctypes.c_wchar_p])
        self._lmc1_ChangeTextByName = _bind("lmc1_ChangeTextByName", [ctypes.c_wchar_p, ctypes.c_wchar_p])
        self._lmc1_Mark = _bind("lmc1_Mark", [ctypes.c_int])
        self._lmc1_StopMark = _bind("lmc1_StopMark", [])
        self._lmc1_GetEntityCount = _bind("lmc1_GetEntityCount", [])
        self._lmc1_GetEntityName = _bind("lmc1_GetEntityName", [ctypes.c_int, ctypes.c_wchar_p])

    def initialize(self, ezcad_dir: Optional[str] = None, test_mode: bool = False, hwnd: Optional[int] = None) -> None:
        target_dir = ezcad_dir or self.ezcad_dir

        # Ensure current working directory is ezcad_dir for MarkEzd dependent resource loading
        if os.path.isdir(target_dir):
            try:
                os.chdir(target_dir)
            except Exception:
                pass

        # MarkEzd requires a valid window handle. Create a lightweight static HWND if none provided.
        actual_hwnd = hwnd
        if not actual_hwnd:
            try:
                actual_hwnd = ctypes.windll.user32.CreateWindowExW(
                    0, "STATIC", "RFID_EzCAD_Owner", 0, 0, 0, 0, 0, 0, 0, 0, 0
                )
            except Exception:
                actual_hwnd = 0

        rc = -1
        if self._lmc1_Initial:
            rc = self._lmc1_Initial(target_dir, int(test_mode), ctypes.c_void_p(actual_hwnd))
        elif self._lmc1_Initial2:
            rc = self._lmc1_Initial2(target_dir, int(test_mode))
        else:
            raise EZCADError(11, "Initialize", "lmc1_Initial export not found in MarkEzd.dll")

        if rc != 0:
            raise EZCADError(rc, "lmc1_Initial")
        self.initialized = True

    def load_template(self, ezd_path: str) -> None:
        if not self.initialized:
            raise EZCADError(11, "load_template", "Driver not initialized")

        resolved_ezd = str(Path(ezd_path).resolve())
        if not os.path.isfile(resolved_ezd):
            raise FileNotFoundError(f"Template file not found: {resolved_ezd}")

        rc = self._lmc1_LoadEzdFile(resolved_ezd)
        if rc != 0:
            raise EZCADError(rc, "lmc1_LoadEzdFile", resolved_ezd)

        self.loaded_template = resolved_ezd
        self._entities = self._query_entities()

    def _query_entities(self) -> List[str]:
        if not self._lmc1_GetEntityCount or not self._lmc1_GetEntityName:
            return []
        count = self._lmc1_GetEntityCount()
        names = []
        buf = ctypes.create_unicode_buffer(256)
        for i in range(count):
            buf.value = ""
            self._lmc1_GetEntityName(i, buf)
            names.append(buf.value)
        return names

    def list_entities(self) -> List[str]:
        if not self._entities:
            self._entities = self._query_entities()
        return list(self._entities)

    def change_text(self, entity_name: str, new_text: str) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "Laser driver not initialized"

        # Find entity name matching case-insensitively
        target_name = entity_name
        current_entities = self.list_entities()
        for ent in current_entities:
            if ent.lower() == entity_name.lower():
                target_name = ent
                break

        rc = self._lmc1_ChangeTextByName(target_name, new_text)
        if rc != 0:
            err_msg = EZCAD_ERROR_MESSAGES.get(rc, f"Code {rc}")
            return False, f"ChangeTextByName('{target_name}') failed: {err_msg}"
        return True, f"Updated entity '{target_name}' -> '{new_text}'"

    def mark(self, fly_mark: bool = False) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "Laser driver not initialized"

        t0 = time.time()
        rc = self._lmc1_Mark(int(fly_mark))
        self.last_mark_duration = time.time() - t0

        if rc != 0:
            err_msg = EZCAD_ERROR_MESSAGES.get(rc, f"Code {rc}")
            return False, f"Laser marking failed: {err_msg} (Exit code: {rc})"
        return True, f"Laser marking completed successfully in {self.last_mark_duration:.2f}s (Hardware Feedback: OK)"


    def stop_mark(self) -> None:
        if self._lmc1_StopMark:
            try:
                self._lmc1_StopMark()
            except Exception:
                pass

    def close(self) -> None:
        if self.initialized and self._lmc1_Close:
            try:
                self._lmc1_Close()
            except Exception:
                pass
            self.initialized = False

    def is_initialized(self) -> bool:
        return self.initialized


class SimulationEzcadDriver(BaseLaserDriver):
    """Software simulation driver allowing testing without physical laser hardware."""

    def __init__(self, ezcad_dir: str):
        self.ezcad_dir = ezcad_dir
        self.initialized = False
        self.is_simulation = True
        self.fallback_reason = None
        self.loaded_template: Optional[str] = None
        self.entities = ["t1", "T1", "barcode1", "date_stamp"]
        self.current_values = {"t1": "DEMO_TAG_1234567890"}
        self.last_mark_duration = 0.0

    def initialize(self, ezcad_dir: Optional[str] = None, test_mode: bool = False, hwnd: Optional[int] = None) -> None:
        self.initialized = True

    def load_template(self, ezd_path: str) -> None:
        if not self.initialized:
            raise EZCADError(11, "load_template", "Driver not initialized")
        self.loaded_template = str(Path(ezd_path).resolve())

    def list_entities(self) -> List[str]:
        return list(self.entities)

    def change_text(self, entity_name: str, new_text: str) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "Driver not initialized"
        matched = False
        for ent in self.entities:
            if ent.lower() == entity_name.lower():
                self.current_values[ent] = new_text
                matched = True
                break
        if not matched:
            self.entities.append(entity_name)
            self.current_values[entity_name] = new_text

        return True, f"[SIMULATION] Updated entity '{entity_name}' -> '{new_text}'"

    def mark(self, fly_mark: bool = False) -> Tuple[bool, str]:
        if not self.initialized:
            return False, "Driver not initialized"
        t0 = time.time()
        time.sleep(1.0)  # Simulate physical laser marking trajectory
        self.last_mark_duration = time.time() - t0
        return True, f"[SIMULATION] Laser marking completed successfully in {self.last_mark_duration:.2f}s (Feedback: OK)"

    def stop_mark(self) -> None:
        pass

    def close(self) -> None:
        self.initialized = False

    def is_initialized(self) -> bool:
        return self.initialized


def create_laser_driver(
    ezcad_dir: str,
    simulation_mode: bool = False,
    hwnd: Optional[int] = None,
    allow_simulation_fallback: bool = True,
) -> BaseLaserDriver:
    """Factory creating appropriate laser driver instance.

    If simulation_mode is True, returns an initialized SimulationEzcadDriver.
    If simulation_mode is False, attempts to initialize HardwareEzcadDriver.
    If hardware initialization fails (e.g. no board plugged in, error 3/4) and
    allow_simulation_fallback is True, gracefully falls back to SimulationEzcadDriver
    with fallback_reason set.
    """
    if simulation_mode:
        driver = SimulationEzcadDriver(ezcad_dir)
        driver.initialize(ezcad_dir, hwnd=hwnd)
        return driver

    try:
        hw = HardwareEzcadDriver(ezcad_dir)
        hw.initialize(ezcad_dir, test_mode=False, hwnd=hwnd)
        return hw
    except Exception as exc:
        if allow_simulation_fallback:
            sim = SimulationEzcadDriver(ezcad_dir)
            sim.initialize(ezcad_dir, hwnd=hwnd)
            setattr(sim, "fallback_reason", str(exc))
            return sim
        raise
