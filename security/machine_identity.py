import hashlib
import json
import subprocess
import sys
from functools import lru_cache


def _normalize(value: str) -> str:
    if not value:
        return ""

    return " ".join(
        value.strip().upper().split()
    )


def _run_powershell_single(command: str) -> str:
    """Run one background PowerShell query without showing a console window."""
    try:
        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": 10,
            "check": False,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            **kwargs,
        )

        if result.returncode != 0:
            return ""

        return result.stdout.strip()

    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ):
        return ""


@lru_cache(maxsize=1)
def get_machine_identity() -> dict:
    """
    Collect machine identifiers from Windows in a single hidden PowerShell call.

    Returns a normalized dictionary.
    """
    query = (
        "[pscustomobject]@{"
        "system_uuid=(Get-CimInstance Win32_ComputerSystemProduct).UUID;"
        "motherboard_serial=(Get-CimInstance Win32_BaseBoard).SerialNumber;"
        "bios_serial=(Get-CimInstance Win32_BIOS).SerialNumber;"
        "system_manufacturer=(Get-CimInstance Win32_ComputerSystem).Manufacturer;"
        "system_model=(Get-CimInstance Win32_ComputerSystem).Model"
        "} | ConvertTo-Json -Compress"
    )

    raw_output = _run_powershell_single(query)
    if not raw_output:
        return {
            "system_uuid": "",
            "motherboard_serial": "",
            "bios_serial": "",
            "system_manufacturer": "",
            "system_model": "",
        }

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError:
        return {
            "system_uuid": "",
            "motherboard_serial": "",
            "bios_serial": "",
            "system_manufacturer": "",
            "system_model": "",
        }

    return {
        "system_uuid": _normalize(str(payload.get("system_uuid", ""))),
        "motherboard_serial": _normalize(str(payload.get("motherboard_serial", ""))),
        "bios_serial": _normalize(str(payload.get("bios_serial", ""))),
        "system_manufacturer": _normalize(str(payload.get("system_manufacturer", ""))),
        "system_model": _normalize(str(payload.get("system_model", ""))),
    }


def create_fingerprint(identity: dict) -> str:
    """
    Create a deterministic SHA-256 fingerprint
    from the canonical machine identity.
    """

    canonical_data = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()