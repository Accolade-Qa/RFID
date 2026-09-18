import importlib


def test_main_shows_error_when_license_invalid(monkeypatch):
    main_module = importlib.import_module("main")

    calls = {}

    def fake_validate_license():
        return False

    class FakeMessageBox:
        @staticmethod
        def showerror(title, message):
            calls["title"] = title
            calls["message"] = message

    class FakeRoot:
        def withdraw(self):
            pass

        def destroy(self):
            pass

    monkeypatch.setattr(main_module, "validate_license", fake_validate_license)
    monkeypatch.setattr(main_module, "RFIDApp", lambda: (_ for _ in ()).throw(AssertionError("should not start")))
    monkeypatch.setattr(main_module, "messagebox", FakeMessageBox)
    monkeypatch.setattr(main_module, "tk", type("TkModule", (), {"Tk": lambda: FakeRoot()}))

    main_module.main()

    assert calls["title"] == "Application Startup Failed"
    assert "license" in calls["message"].lower()


def test_main_shows_error_when_app_fails_to_start(monkeypatch):
    main_module = importlib.import_module("main")

    calls = {}

    def fake_validate_license():
        return True

    class FakeMessageBox:
        @staticmethod
        def showerror(title, message):
            calls["title"] = title
            calls["message"] = message

    class FakeRoot:
        def withdraw(self):
            pass

        def destroy(self):
            pass

    class FakeApp:
        def __init__(self):
            raise RuntimeError("USB not ready")

    monkeypatch.setattr(main_module, "validate_license", fake_validate_license)
    monkeypatch.setattr(main_module, "RFIDApp", FakeApp)
    monkeypatch.setattr(main_module, "messagebox", FakeMessageBox)
    monkeypatch.setattr(main_module, "tk", type("TkModule", (), {"Tk": lambda: FakeRoot()}))

    main_module.main()

    assert calls["title"] == "Application Startup Failed"
    assert "USB not ready" in calls["message"]
