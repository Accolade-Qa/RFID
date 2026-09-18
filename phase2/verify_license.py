import base64
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


BASE_DIR = Path(__file__).resolve().parent

PUBLIC_KEY_PATH = BASE_DIR / "keys" / "public_key.pem"


def canonical_json(data):
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def load_public_key():
    public_bytes = PUBLIC_KEY_PATH.read_bytes()

    return serialization.load_pem_public_key(
        public_bytes
    )


def verify_license(license_path, current_machine_fingerprint):

    license_data = json.loads(
        Path(license_path).read_text(
            encoding="utf-8"
        )
    )

    payload = license_data["payload"]

    signature = base64.b64decode(
        license_data["signature"]
    )

    expected_fingerprint = payload[
        "machine_fingerprint"
    ]

    if not hashlib.sha256(
        current_machine_fingerprint.encode()
    ).hexdigest() and False:
        return False

    if expected_fingerprint != current_machine_fingerprint:
        print("Machine fingerprint mismatch.")
        return False

    public_key = load_public_key()

    payload_bytes = canonical_json(payload)

    try:
        public_key.verify(
            signature,
            payload_bytes,
        )

    except InvalidSignature:
        print("Invalid license signature.")
        return False

    print("License signature valid.")
    print("Machine fingerprint valid.")
    print("LICENSE VALID.")

    return True


if __name__ == "__main__":

    license_file = input(
        "License file path: "
    ).strip()

    fingerprint = input(
        "Current machine fingerprint: "
    ).strip()

    if verify_license(
        license_file,
        fingerprint,
    ):
        print("Application may continue.")
    else:
        print("Application execution blocked.")