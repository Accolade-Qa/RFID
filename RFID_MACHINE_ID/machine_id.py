import hashlib
import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


APP_NAME = "RFID Machine ID"


def run_powershell(command: str) -> str:
    """
    Execute a read-only PowerShell/CIM query.
    Returns an empty string if the query fails.
    """

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
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


def normalize(value: str) -> str:
    """
    Normalize identifier values before fingerprinting.
    """

    if not value:
        return ""

    return " ".join(
        value.strip().upper().split()
    )


def get_machine_identity() -> dict:
    """
    Collect machine identifiers.
    """

    system_uuid = run_powershell(
        "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
    )

    motherboard_serial = run_powershell(
        "(Get-CimInstance Win32_BaseBoard).SerialNumber"
    )

    bios_serial = run_powershell(
        "(Get-CimInstance Win32_BIOS).SerialNumber"
    )

    manufacturer = run_powershell(
        "(Get-CimInstance Win32_ComputerSystem).Manufacturer"
    )

    model = run_powershell(
        "(Get-CimInstance Win32_ComputerSystem).Model"
    )

    return {
        "system_uuid": normalize(system_uuid),
        "motherboard_serial": normalize(
            motherboard_serial
        ),
        "bios_serial": normalize(
            bios_serial
        ),
        "system_manufacturer": normalize(
            manufacturer
        ),
        "system_model": normalize(
            model
        ),
    }


def create_fingerprint(identity: dict) -> str:
    """
    Generate a deterministic SHA-256 fingerprint.
    """

    canonical_data = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical_data.encode("utf-8")
    ).hexdigest()


def create_machine_file():
    """
    Collect machine identity and create
    a uniquely named machine ID file.
    """

    identity = get_machine_identity()

    fingerprint = create_fingerprint(
        identity
    )

    output = {
        "version": 1,
        "product": "RFID Utility",
        "machine": identity,
        "fingerprint": fingerprint,
    }

    # Use first 8 characters only for the filename.
    # The complete fingerprint remains inside the JSON.
    fingerprint_short = fingerprint[:8].upper()

    output_filename = (
        f"RFID_Machine_ID_{fingerprint_short}.json"
    )

    output_path = (
        Path.cwd() / output_filename
    )

    output_path.write_text(
        json.dumps(
            output,
            indent=4,
        ),
        encoding="utf-8",
    )

    return output_path, fingerprint


def main():
    try:
        output_path, fingerprint = (
            create_machine_file()
        )

        root = tk.Tk()
        root.withdraw()

        messagebox.showinfo(
            APP_NAME,
            "Machine ID generated successfully.\n\n"
            f"File:\n{output_path.name}\n\n"
            "Please send this file to the "
            "RFID administrator.",
        )

        root.destroy()

    except Exception as exc:
        root = tk.Tk()
        root.withdraw()

        messagebox.showerror(
            APP_NAME,
            "Failed to collect machine information.\n\n"
            f"Error: {exc}",
        )

        root.destroy()

        sys.exit(1)


if __name__ == "__main__":
    main()