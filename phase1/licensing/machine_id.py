"""Windows machine-identifier collection.

This module intentionally exposes normalized identifier values only to the
local licensing code. It does not send identifiers anywhere.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MachineIdentifiers:
    """Raw/normalized identifiers collected from the local Windows machine."""

    system_uuid: Optional[str]
    motherboard_serial: Optional[str]
    bios_serial: Optional[str]
    system_manufacturer: Optional[str]
    system_model: Optional[str]

    def available(self) -> dict[str, str]:
        values = {
            "system_uuid": self.system_uuid,
            "motherboard_serial": self.motherboard_serial,
            "bios_serial": self.bios_serial,
            "system_manufacturer": self.system_manufacturer,
            "system_model": self.system_model,
        }
        return {k: v for k, v in values.items() if v}


def _normalize(value: object) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Normalize whitespace/case and common placeholder values.
    text = " ".join(text.split()).upper()
    placeholders = {
        "NONE",
        "UNKNOWN",
        "DEFAULT STRING",
        "TO BE FILLED BY O.E.M.",
        "TO BE FILLED BY OEM",
        "SYSTEM SERIAL NUMBER",
        "NOT SPECIFIED",
        "NOT AVAILABLE",
    }
    if text in placeholders:
        return None

    return text


def _powershell_value(command: str) -> Optional[str]:
    """Run a read-only PowerShell command and return one normalized value."""
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return _normalize(completed.stdout)


def collect_machine_identifiers() -> MachineIdentifiers:
    """Collect stable identifiers on Windows using read-only CIM queries."""
    if platform.system().lower() != "windows":
        raise RuntimeError("Phase 1 currently supports Windows only.")

    system_uuid = _powershell_value(
        "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
    )
    motherboard_serial = _powershell_value(
        "(Get-CimInstance Win32_BaseBoard).SerialNumber"
    )
    bios_serial = _powershell_value(
        "(Get-CimInstance Win32_BIOS).SerialNumber"
    )
    manufacturer = _powershell_value(
        "(Get-CimInstance Win32_ComputerSystem).Manufacturer"
    )
    model = _powershell_value(
        "(Get-CimInstance Win32_ComputerSystem).Model"
    )

    return MachineIdentifiers(
        system_uuid=system_uuid,
        motherboard_serial=motherboard_serial,
        bios_serial=bios_serial,
        system_manufacturer=manufacturer,
        system_model=model,
    )


def identifier_digest(value: str) -> str:
    """Return a SHA-256 digest of a normalized identifier."""
    normalized = _normalize(value)
    if normalized is None:
        raise ValueError("Cannot hash an empty/placeholder identifier.")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
