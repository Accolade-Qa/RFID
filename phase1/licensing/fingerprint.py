"""Deterministic machine fingerprint generation.

Phase 1 deliberately keeps this separate from license signing. The resulting
fingerprint will become an input to the signed license in Phase 2/3.
"""

from __future__ import annotations

import hashlib
from .machine_id import MachineIdentifiers, collect_machine_identifiers


# These are the identifiers we consider in the initial design.
# The exact weighting/fallback policy should be finalized after testing on the
# actual target hardware population.
FINGERPRINT_FIELDS = (
    "system_uuid",
    "motherboard_serial",
    "bios_serial",
    "system_manufacturer",
    "system_model",
)


def _canonical_material(ids: MachineIdentifiers) -> str:
    values = []
    for field in FINGERPRINT_FIELDS:
        value = getattr(ids, field)
        if value:
            values.append(f"{field}={value}")
    return "\n".join(values)


def fingerprint_from_identifiers(ids: MachineIdentifiers) -> str:
    """Create a deterministic SHA-256 fingerprint from available identifiers."""
    material = _canonical_material(ids)

    if not material:
        raise RuntimeError(
            "No usable machine identifiers were found; cannot create "
            "a machine fingerprint."
        )

    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def get_machine_fingerprint() -> str:
    """Collect local identifiers and return the machine fingerprint."""
    return fingerprint_from_identifiers(collect_machine_identifiers())


def get_fingerprint_material_for_diagnostics() -> dict[str, str]:
    """Return available values for local diagnostics only.

    Do not place these raw values into a distributed license unless there is a
    specific reason. The signed license can contain only the fingerprint.
    """
    ids = collect_machine_identifiers()
    return ids.available()
