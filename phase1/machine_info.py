"""Phase 1 diagnostic utility.

Run on the target Windows machine:
    python machine_info.py

This prints the identifiers found locally and the resulting fingerprint.
The output is for provisioning/testing and should be treated as machine data.
"""

from phase1.licensing.fingerprint import (
    get_machine_fingerprint,
    get_fingerprint_material_for_diagnostics,
)


def main() -> None:
    print("=== Phase 1: Machine Identity Diagnostic ===")
    print()

    try:
        identifiers = get_fingerprint_material_for_diagnostics()
        if not identifiers:
            print("No usable identifiers were found.")
            return

        print("Available identifiers:")
        for name, value in identifiers.items():
            print(f"  {name}: {value}")

        print()
        print("Machine fingerprint (SHA-256):")
        print(f"  {get_machine_fingerprint()}")
        print()
        print("This phase performs local, read-only collection only.")
        print("No network connection is used.")
    except Exception as exc:
        print(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
