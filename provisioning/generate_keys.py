from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives import serialization


BASE_DIR = Path(__file__).resolve().parent.parent

KEY_DIR = BASE_DIR / "keys"


def generate_keys():
    KEY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    private_key = (
        Ed25519PrivateKey.generate()
    )

    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path = (
        KEY_DIR / "private_key.pem"
    )

    public_path = (
        KEY_DIR / "public_key.pem"
    )

    private_path.write_bytes(
        private_bytes
    )

    public_path.write_bytes(
        public_bytes
    )

    print("Key pair generated.")
    print()
    print(f"Private key: {private_path}")
    print(f"Public key : {public_path}")
    print()
    print(
        "IMPORTANT: Never distribute the private key."
    )


if __name__ == "__main__":
    generate_keys()