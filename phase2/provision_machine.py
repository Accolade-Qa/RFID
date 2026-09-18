import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization


BASE_DIR = Path(__file__).resolve().parent
KEY_DIR = BASE_DIR / "keys"
LICENSE_DIR = BASE_DIR / "licenses"

PRIVATE_KEY_PATH = KEY_DIR / "private_key.pem"


def load_private_key():
    private_bytes = PRIVATE_KEY_PATH.read_bytes()

    return serialization.load_pem_private_key(
        private_bytes,
        password=None,
    )


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def create_license(machine_fingerprint):
    private_key = load_private_key()

    payload = {
        "version": 1,
        "product": "RFID Utility",
        "machine_fingerprint": machine_fingerprint,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "license_id": str(uuid.uuid4()),
    }

    payload_bytes = canonical_json(payload)

    signature = private_key.sign(payload_bytes)

    license_data = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }

    LICENSE_DIR.mkdir(exist_ok=True)

    output_file = (
        LICENSE_DIR /
        f"{machine_fingerprint[:16]}.license.json"
    )

    output_file.write_text(
        json.dumps(license_data, indent=4),
        encoding="utf-8",
    )

    print("License created successfully.")
    print(f"License: {output_file}")


if __name__ == "__main__":
    fingerprint = input(
        "Enter the Phase 1 machine fingerprint: "
    ).strip()

    if not fingerprint:
        raise ValueError("Machine fingerprint cannot be empty.")

    create_license(fingerprint)