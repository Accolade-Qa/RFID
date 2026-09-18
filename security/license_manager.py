import base64
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

from .machine_identity import (
    create_fingerprint,
    get_machine_identity,
)


def get_app_directory() -> Path:
    """
    Return the directory where the application is running from.

    Development:
        RFID/
        ├── main.py
        └── license/

    PyInstaller:
        RFID/
        ├── RFID.exe
        └── license/
    """

    if getattr(sys, "frozen", False):
        # PyInstaller executable location
        return Path(sys.executable).resolve().parent

    # Normal Python execution
    return Path(__file__).resolve().parent.parent


APP_DIR = get_app_directory()

# Runtime license layout:
# <app_dir>/license/<machine_folder>/license/license.json
# or, in the project tree, <project_root>/license/<fingerprint>/license/license.json
# The app should read the license from the machine-specific folder that is bundled
# alongside the EXE. We keep a fixed lookup path based on the executable directory.
LICENSE_PATH = (
    APP_DIR / "license" / "license.json"
)


def get_license_path() -> Path:
    """Resolve the active license file in the deployed app layout."""
    candidate_paths = [
        APP_DIR / "license" / "license.json",
        APP_DIR / "license" / "license" / "license.json",
    ]

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate

    return candidate_paths[0]


PUBLIC_KEY = b"""
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAKG7ooEJhsiqFc3fmsy7PuMR4xv4XfQblQiKu5C33PsE=
-----END PUBLIC KEY-----
"""


def _canonical_json(data: dict) -> bytes:
    """
    Convert dictionary to deterministic JSON bytes.

    The exact same representation must be used
    when creating and verifying the signature.
    """

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _load_public_key():
    """
    Load the embedded Ed25519 public key.
    """

    return serialization.load_pem_public_key(
        PUBLIC_KEY
    )


def _load_license() -> dict | None:
    """
    Load the external license file.

    The license is expected at:

        <application folder>/license/license.json
    """

    try:
        resolved_license_path = get_license_path()
        if not resolved_license_path.exists():
            return None

        return json.loads(
            resolved_license_path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None


def _verify_signature(
    license_data: dict,
) -> bool:
    """
    Verify the Ed25519 signature over the license payload.
    """

    try:
        payload = license_data["payload"]

        signature_text = (
            license_data["signature"]
        )

        signature = base64.b64decode(
            signature_text,
            validate=True,
        )

        payload_bytes = _canonical_json(
            payload
        )

        public_key = _load_public_key()

        public_key.verify(
            signature,
            payload_bytes,
        )

        return True

    except (
        KeyError,
        ValueError,
        TypeError,
        InvalidSignature,
    ):
        return False


def validate_license() -> bool:
    """
    Validate the installed RFID license.

    Validation sequence:

    1. Load license.json
    2. Verify Ed25519 signature
    3. Read licensed fingerprint
    4. Read current machine identity
    5. Generate current fingerprint
    6. Compare fingerprints

    Returns:
        True  -> license is valid
        False -> license is invalid
    """

    license_data = _load_license()

    if license_data is None:
        return False

    if not _verify_signature(
        license_data
    ):
        return False

    try:
        payload = license_data["payload"]

        licensed_fingerprint = (
            payload["fingerprint"]
        )

    except (
        KeyError,
        TypeError,
    ):
        return False

    current_identity = (
        get_machine_identity()
    )

    current_fingerprint = (
        create_fingerprint(
            current_identity
        )
    )

    if (
        current_fingerprint
        != licensed_fingerprint
    ):
        return False

    return True