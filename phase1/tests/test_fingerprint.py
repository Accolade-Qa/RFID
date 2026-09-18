import pytest

from phase1.licensing.fingerprint import fingerprint_from_identifiers
from phase1.licensing.machine_id import MachineIdentifiers, identifier_digest


def test_same_identifiers_produce_same_fingerprint():
    ids = MachineIdentifiers(
        system_uuid="ABC-123",
        motherboard_serial="BOARD-1",
        bios_serial="BIOS-1",
        system_manufacturer="ACME",
        system_model="MODEL-X",
    )

    assert fingerprint_from_identifiers(ids) == fingerprint_from_identifiers(ids)


def test_fingerprint_changes_when_identifier_changes():
    first = MachineIdentifiers(
        system_uuid="ABC-123",
        motherboard_serial="BOARD-1",
        bios_serial="BIOS-1",
        system_manufacturer="ACME",
        system_model="MODEL-X",
    )
    second = MachineIdentifiers(
        system_uuid="DIFFERENT",
        motherboard_serial="BOARD-1",
        bios_serial="BIOS-1",
        system_manufacturer="ACME",
        system_model="MODEL-X",
    )

    assert fingerprint_from_identifiers(first) != fingerprint_from_identifiers(second)


def test_placeholder_values_are_ignored():
    ids = MachineIdentifiers(
        system_uuid="DEFAULT STRING",
        motherboard_serial="",
        bios_serial=None,
        system_manufacturer="ACME",
        system_model="MODEL-X",
    )

    fingerprint = fingerprint_from_identifiers(ids)
    assert len(fingerprint) == 64


def test_no_identifiers_fails():
    ids = MachineIdentifiers(None, None, None, None, None)

    with pytest.raises(RuntimeError):
        fingerprint_from_identifiers(ids)


def test_identifier_digest_is_deterministic_and_sha256():
    digest = identifier_digest("ABC-123")
    assert len(digest) == 64
    assert digest == identifier_digest("abc-123")
