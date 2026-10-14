"""Header component with application branding and status indicators."""

import tkinter as tk
from tkinter import ttk


class HeaderComponent(ttk.Frame):
    """Top banner with app branding and status badges."""

    def __init__(self, parent, is_simulation: bool = False):
        super().__init__(parent, padding=(12, 10))
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        title_frame = ttk.Frame(self)
        title_frame.grid(row=0, column=0, sticky="w")

        title_lbl = tk.Label(
            title_frame,
            text="AEPL RFID LASER MARKING UTILITY",
            font=("Segoe UI", 14, "bold"),
            fg="#1E3A8A",
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            title_frame,
            text="EzCAD 2.14.11 Integration | Windows 7 32-bit Compatible",
            font=("Segoe UI", 9),
            fg="#4B5563",
        )
        sub_lbl.pack(anchor="w")

        # Status badge frame
        badge_frame = ttk.Frame(self)
        badge_frame.grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.mode_badge = tk.Label(
            badge_frame,
            text="SIMULATION MODE" if is_simulation else "HARDWARE MODE",
            font=("Segoe UI", 9, "bold"),
            bg="#FEF3C7" if is_simulation else "#DCFCE7",
            fg="#92400E" if is_simulation else "#166534",
            padx=10,
            pady=4,
            relief="groove",
            borderwidth=1,
        )
        self.mode_badge.pack(anchor="e")

    def update_mode(self, is_simulation: bool):
        if is_simulation:
            self.mode_badge.config(
                text="SIMULATION MODE",
                bg="#FEF3C7",
                fg="#92400E",
            )
        else:
            self.mode_badge.config(
                text="HARDWARE MODE",
                bg="#DCFCE7",
                fg="#166534",
            )
