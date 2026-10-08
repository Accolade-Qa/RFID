from __future__ import annotations

import ctypes
from pathlib import Path


# MarkEzd.dll uses 32-bit exports and the EZCAD SDK documents TCHAR as Unicode.
# This wrapper therefore uses a 32-bit Python interpreter and c_wchar_p.
class EZCADError(RuntimeError):
    pass


ERRORS = {
    0: "SUCCESS",
    1: "EZCAD is already running",
    2: "EZCAD.CFG not found",
    3: "Failed to open LMC1",
    4: "No valid LMC1 device",
    5: "LMC1 hardware version error",
    6: "Device configuration not found",
    7: "Stop/alarm signal",
    8: "User stopped",
    9: "Unknown error",
    10: "Timeout",
    11: "Not initialized",
    12: "Failed to read EZD file",
    13: "Owner window is null",
    14: "Font not found",
    15: "Invalid pen number",
    16: "Specified object is not a text object",
    17: "Failed to save file",
    18: "Specified object not found",
    19: "Operation is not allowed in current state",
}


class EZCAD:
    """Direct ctypes wrapper for the flat lmc1_* exports in MarkEzd.dll."""

    def __init__(self, dll_path: str | Path):
        self.dll_path = Path(dll_path).resolve()
        if not self.dll_path.exists():
            raise FileNotFoundError(self.dll_path)

        # MarkEzd.dll is PE32. Python itself must therefore be 32-bit.
        if ctypes.sizeof(ctypes.c_void_p) != 4:
            raise RuntimeError(
                "MarkEzd.dll is 32-bit. Run this application with 32-bit Python."
            )

        # Make DLL dependencies (Lmc1.dll etc.) resolvable from the EZCAD directory.
        self._dll_dir = self.dll_path.parent
        if hasattr(os := __import__("os"), "add_dll_directory"):
            self._dll_search = os.add_dll_directory(str(self._dll_dir))

        try:
            try:
                ctypes.windll.kernel32.SetDllDirectoryW(str(self._dll_dir))
            except Exception:
                pass
            self.dll = ctypes.WinDLL(str(self.dll_path))
        except OSError as exc:
            winerror = getattr(exc, "winerror", None)
            if winerror == 127:
                raise EZCADError(
                    f"Failed to load {self.dll_path.name} (WinError 127: The specified procedure could not be found).\n"
                    f"This indicates a version mismatch between MarkEzd.dll and the EZCAD runtime DLLs (Lmc1.dll / DataMgr.dll) in '{self._dll_dir}'.\n"
                    f"The MarkEzd.dll being loaded expects different function signatures than what is provided by your EZCAD installation.\n"
                    f"Please ensure MarkEzd.dll is the version specifically provided for your EZCAD 2.14.11 release."
                ) from exc
            if winerror == 126:
                raise EZCADError(
                    f"Failed to load {self.dll_path.name} (WinError 126: The specified module could not be found).\n"
                    f"Ensure that dependent DLLs (such as Lmc1.dll, DataMgr.dll, mathlib.dll) exist in '{self._dll_dir}'."
                ) from exc
            raise

        self._bind_functions()
        self.initialized = False

    def _bind_functions(self) -> None:
        self.lmc1_Initial = self.dll.lmc1_Initial
        self.lmc1_Initial.argtypes = [
            ctypes.c_wchar_p,  # strEzCadPath
            ctypes.c_int,      # BOOL bTestMode
            ctypes.c_void_p,   # HWND hOwenWnd
        ]
        self.lmc1_Initial.restype = ctypes.c_int

        self.lmc1_Initial2 = self.dll.lmc1_Initial2
        self.lmc1_Initial2.argtypes = [
            ctypes.c_wchar_p,  # strEzCadPath
            ctypes.c_int,      # BOOL bTestMode
        ]
        self.lmc1_Initial2.restype = ctypes.c_int

        self.lmc1_Close = self.dll.lmc1_Close
        self.lmc1_Close.argtypes = []
        self.lmc1_Close.restype = ctypes.c_int

        self.lmc1_LoadEzdFile = self.dll.lmc1_LoadEzdFile
        self.lmc1_LoadEzdFile.argtypes = [ctypes.c_wchar_p]
        self.lmc1_LoadEzdFile.restype = ctypes.c_int

        self.lmc1_ChangeTextByName = self.dll.lmc1_ChangeTextByName
        self.lmc1_ChangeTextByName.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
        ]
        self.lmc1_ChangeTextByName.restype = ctypes.c_int

        self.lmc1_Mark = self.dll.lmc1_Mark
        self.lmc1_Mark.argtypes = [ctypes.c_int]  # BOOL bFlyMark
        self.lmc1_Mark.restype = ctypes.c_int

        self.lmc1_Reset = self.dll.lmc1_Reset
        self.lmc1_Reset.argtypes = [ctypes.c_ushort, ctypes.c_ushort]
        self.lmc1_Reset.restype = ctypes.c_int

        self.lmc1_StopMark = self.dll.lmc1_StopMark
        self.lmc1_StopMark.argtypes = []
        self.lmc1_StopMark.restype = ctypes.c_int

    @staticmethod
    def _check(rc: int, operation: str) -> None:
        if rc != 0:
            detail = ERRORS.get(rc, f"Unknown EZCAD error code {rc}")
            raise EZCADError(f"{operation} failed: code={rc} ({detail})")

    def initial(self, ezcad_dir: str | Path, test_mode: bool = False) -> None:
        # Initial2 is the DLL's own wrapper around:
        # lmc1_Initial(path, testMode, NULL)
        path = str(Path(ezcad_dir).resolve())
        rc = self.lmc1_Initial2(path, int(test_mode))
        self._check(rc, "lmc1_Initial2")
        self.initialized = True

    def load_template(self, ezd_path: str | Path) -> None:
        path = str(Path(ezd_path).resolve())
        if not Path(path).exists():
            raise FileNotFoundError(path)
        self._check(self.lmc1_LoadEzdFile(path), "lmc1_LoadEzdFile")

    def change_text(self, object_name: str, text: str) -> None:
        self._check(
            self.lmc1_ChangeTextByName(object_name, text),
            f"lmc1_ChangeTextByName({object_name!r})",
        )

    def mark(self, fly_mark: bool = False) -> None:
        # EZCAD's documented lmc1_Mark call waits until the device finishes
        # the marking operation before returning.
        self._check(self.lmc1_Mark(int(fly_mark)), "lmc1_Mark")

    def stop_mark(self) -> None:
        self._check(self.lmc1_StopMark(), "lmc1_StopMark")

    def close(self) -> None:
        if self.initialized:
            rc = self.lmc1_Close()
            self.initialized = False
            self._check(rc, "lmc1_Close")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        except Exception:
            pass
