import tkinter as tk
from tkinter import messagebox

from security import validate_license
from ui.app import RFIDApp


def _show_startup_error(message: str):
    """Display a user-friendly popup for startup failures."""
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror(
            "Application Startup Failed",
            message,
        )
    finally:
        root.destroy()


def main():
    try:
        if not validate_license():
            message = (
                "The application license is invalid, missing, expired, or not "
                "authorized for this computer.\n\n"
                "Please contact the administrator for activation or installation help."
            )
            _show_startup_error(message)
            print("License validation failed. This application is not authorized for this computer.")
            return

        app = RFIDApp()
        app.run()
    except Exception as exc:
        message = (
            "The application could not start successfully.\n\n"
            f"Reason: {exc}\n\n"
            "Please verify the license, device configuration, and environment settings."
        )
        _show_startup_error(message)
        print(f"Application startup failed: {exc}")


if __name__ == "__main__":
    main()