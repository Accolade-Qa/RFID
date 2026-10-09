from printer import ezcad


def test_winerror_127_does_not_claim_a_specific_version_mismatch(
    tmp_path, monkeypatch
):
    dll_path = tmp_path / "MarkEzd.dll"
    dll_path.touch()
    load_error = OSError("The specified procedure could not be found")
    load_error.winerror = 127

    def fail_to_load(_path):
        raise load_error

    monkeypatch.setattr(ezcad.ctypes, "sizeof", lambda _type: 4)
    monkeypatch.setattr(ezcad.ctypes, "WinDLL", fail_to_load, raising=False)

    try:
        ezcad.EZCAD(dll_path)
    except ezcad.EZCADError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected EZCADError")

    assert "does not identify the DLL or procedure" in message
    assert "function signatures" not in message
