import base64
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

KEY_PATH = (
    PROJECT_ROOT
    / "keys"
    / "private_key.pem"
)

DIST_DIR = (
    PROJECT_ROOT
    / "dist"
)

RFID_EXE = (
    DIST_DIR
    / "RFID.exe"
)

LICENSE_DIR = (
    PROJECT_ROOT
    / "license"
)


# ============================================================
# IMPORT MACHINE ID FUNCTIONS
# ============================================================

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from security.machine_identity import (
    create_fingerprint,
)


# ============================================================
# JSON HELPERS
# ============================================================

def canonical_json(data: dict) -> bytes:
    """
    Convert dictionary to deterministic JSON bytes.
    """

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


# ============================================================
# LOAD CUSTOMER MACHINE ID
# ============================================================

def load_machine_id_file(
    machine_id_path: Path,
) -> dict:

    if not machine_id_path.exists():
        raise FileNotFoundError(
            f"Machine ID file not found:\n"
            f"{machine_id_path}"
        )

    try:
        machine_data = json.loads(
            machine_id_path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise ValueError(
            "Machine ID file contains invalid JSON."
        ) from exc

    if not isinstance(
        machine_data,
        dict,
    ):
        raise ValueError(
            "Machine ID file must contain a JSON object."
        )

    return machine_data


# ============================================================
# VALIDATE MACHINE ID
# ============================================================

def validate_machine_id(
    machine_data: dict,
) -> tuple[dict, str]:

    try:
        identity = machine_data["machine"]

        supplied_fingerprint = (
            machine_data["fingerprint"]
        )

    except KeyError as exc:
        raise ValueError(
            "Machine ID file is missing required fields."
        ) from exc

    if not isinstance(
        identity,
        dict,
    ):
        raise ValueError(
            "'machine' must be a JSON object."
        )

    if not isinstance(
        supplied_fingerprint,
        str,
    ):
        raise ValueError(
            "'fingerprint' must be a string."
        )

    calculated_fingerprint = (
        create_fingerprint(identity)
    )

    if (
        calculated_fingerprint.lower()
        != supplied_fingerprint.lower()
    ):
        raise ValueError(
            "Machine ID validation failed.\n"
            "The fingerprint does not match "
            "the supplied machine information."
        )

    return (
        identity,
        calculated_fingerprint,
    )


# ============================================================
# LOAD PRIVATE KEY
# ============================================================

def load_private_key():

    if not KEY_PATH.exists():
        raise FileNotFoundError(
            "Private key not found:\n"
            f"{KEY_PATH}"
        )

    private_bytes = (
        KEY_PATH.read_bytes()
    )

    return serialization.load_pem_private_key(
        private_bytes,
        password=None,
    )


# ============================================================
# COPY APPLICATION EXE
# ============================================================

def copy_application_exe(
    deployment_dir: Path,
):
    """
    Copy the already-built RFID.exe from dist/
    into the machine-specific deployment folder.
    """

    if not RFID_EXE.exists():
        raise FileNotFoundError(
            "RFID.exe was not found in the dist folder.\n"
            f"Expected location:\n{RFID_EXE}\n\n"
            "Build the application first using PyInstaller."
        )

    destination_exe = (
        deployment_dir
        / "RFID.exe"
    )

    shutil.copy2(
        RFID_EXE,
        destination_exe,
    )

    return destination_exe


# ============================================================
# CREATE LICENSE
# ============================================================

def create_license(
    machine_id_path: Path,
):

    print()
    print(
        "Loading machine ID:"
    )
    print(
        machine_id_path
    )

    # --------------------------------------------------------
    # Load machine data
    # --------------------------------------------------------

    machine_data = (
        load_machine_id_file(
            machine_id_path
        )
    )

    # --------------------------------------------------------
    # Validate machine data
    # --------------------------------------------------------

    identity, fingerprint = (
        validate_machine_id(
            machine_data
        )
    )

    print()
    print(
        "Machine ID validated successfully."
    )

    print(
        f"Fingerprint: {fingerprint}"
    )

    # --------------------------------------------------------
    # Create license payload
    # --------------------------------------------------------

    payload = {
        "version": 1,
        "product": "RFID Utility",
        "license_id": str(
            uuid.uuid4()
        ),
        "issued_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "machine": identity,
        "fingerprint": fingerprint,
    }

    # --------------------------------------------------------
    # Load private signing key
    # --------------------------------------------------------

    private_key = (
        load_private_key()
    )

    # --------------------------------------------------------
    # Sign payload
    # --------------------------------------------------------

    payload_bytes = (
        canonical_json(
            payload
        )
    )

    signature = (
        private_key.sign(
            payload_bytes
        )
    )

    # --------------------------------------------------------
    # Build final license
    # --------------------------------------------------------

    license_data = {
        "payload": payload,
        "signature": base64.b64encode(
            signature
        ).decode("ascii"),
    }

    # --------------------------------------------------------
    # Create machine-specific deployment directory
    # Layout required by the packaged app:
    #
    #   <project>/license/<machine_folder>/RFID.exe
    #   <project>/license/<machine_folder>/license/license.json
    # --------------------------------------------------------

    fingerprint_short = (
        fingerprint[:8].upper()
    )

    deployment_dir = (
        LICENSE_DIR
        / fingerprint_short
    )

    deployment_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    license_dir = (
        deployment_dir
        / "license"
    )
    license_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Copy RFID.exe
    # --------------------------------------------------------

    exe_path = (
        copy_application_exe(
            deployment_dir
        )
    )

    # --------------------------------------------------------
    # Write license
    # --------------------------------------------------------

    license_path = (
        license_dir
        / "license.json"
    )

    license_path.write_text(
        json.dumps(
            license_data,
            indent=4,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )
    print(
        "License created successfully."
    )
    print(
        "========================================"
    )

    print()
    print(
        f"Deployment folder:"
    )
    print(
        deployment_dir
    )

    print()
    print(
        f"RFID.exe:"
    )
    print(
        exe_path
    )

    print()
    print(
        f"license.json:"
    )
    print(
        license_path
    )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python provisioning/provision_machine.py "
            "<machine_id.json>"
        )

        sys.exit(1)

    machine_id_path = (
        Path(sys.argv[1]).resolve()
    )

    try:

        create_license(
            machine_id_path
        )

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as exc:

        print()
        print(
            "ERROR:"
        )
        print(
            exc
        )

        sys.exit(1)


if __name__ == "__main__":
    main()