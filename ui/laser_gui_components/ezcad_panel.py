"""EzCAD Application & File-Binding Configuration Panel."""

import os
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional


class EzcadPanel(ttk.LabelFrame):
    """Panel managing EzCAD GUI executable path, template file, dynamic input text file, and simulation mode."""

    def __init__(
        self,
        parent,
        default_ezcad_exe: str = "Ezcad2.exe",
        default_template: str = "test.ezd",
        default_input_file: str = "tag_input.txt",
        default_delay: float = 1.5,
        default_simulation: bool = False,
        on_launch_ezcad: Optional[Callable[[], None]] = None,
        on_red_light: Optional[Callable[[], None]] = None,
        on_simulation_toggle: Optional[Callable[[bool], None]] = None,
    ):
        super().__init__(parent, text="EzCAD GUI & Dynamic File Binding Configuration", padding=(12, 10))
        self.on_launch_ezcad = on_launch_ezcad
        self.on_red_light = on_red_light
        self.on_simulation_toggle = on_simulation_toggle

        self.columnconfigure(1, weight=1)

        # Row 0: EzCAD Executable (.exe)
        ttk.Label(self, text="EzCAD Exe:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.exe_var = tk.StringVar(value=default_ezcad_exe)
        self.exe_entry = ttk.Entry(self, textvariable=self.exe_var)
        self.exe_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.browse_exe_btn = ttk.Button(self, text="Browse...", width=9, command=self._browse_exe)
        self.browse_exe_btn.grid(row=0, column=2, sticky="e", pady=3)

        # Row 1: EzCAD Template File (.ezd)
        ttk.Label(self, text="Template File:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.template_var = tk.StringVar(value=default_template)
        self.template_entry = ttk.Entry(self, textvariable=self.template_var)
        self.template_entry.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.browse_tmpl_btn = ttk.Button(self, text="Browse...", width=9, command=self._browse_template)
        self.browse_tmpl_btn.grid(row=1, column=2, sticky="e", pady=3)

        # Row 2: Dynamic Input File (.txt) consumed by EzCAD Variable Text
        ttk.Label(self, text="Laser Input File:").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=3)
        self.input_file_var = tk.StringVar(value=default_input_file)
        self.input_file_entry = ttk.Entry(self, textvariable=self.input_file_var)
        self.input_file_entry.grid(row=2, column=1, sticky="ew", padx=(0, 6), pady=3)

        btn_box = ttk.Frame(self)
        btn_box.grid(row=2, column=2, sticky="e", pady=3)
        self.browse_txt_btn = ttk.Button(btn_box, text="Browse...", width=9, command=self._browse_input_file)
        self.browse_txt_btn.pack(side="left", padx=(0, 4))
        self.open_txt_btn = ttk.Button(btn_box, text="Open", width=6, command=self._open_input_file)
        self.open_txt_btn.pack(side="left")

        # Row 3: Settling / Mark Duration & Options
        row3 = ttk.Frame(self)
        row3.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 4))

        ttk.Label(row3, text="Mark Duration (s):").pack(side="left", padx=(0, 4))
        self.delay_var = tk.DoubleVar(value=default_delay)
        self.delay_entry = ttk.Entry(row3, textvariable=self.delay_var, width=5)
        self.delay_entry.pack(side="left", padx=(0, 16))

        # Simulation Mode
        self.sim_var = tk.BooleanVar(value=default_simulation)
        self.sim_chk = ttk.Checkbutton(
            row3,
            text="Simulation Mode (Test without physical laser)",
            variable=self.sim_var,
            command=self._handle_sim_toggle,
        )
        self.sim_chk.pack(side="left", padx=(0, 16))

        # Action shortcuts: Launch/Focus EzCAD, Red Light F1
        self.focus_btn = tk.Button(
            row3,
            text="🪟 Launch / Focus EzCAD",
            bg="#2563EB",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=2,
            command=self._handle_launch_focus,
        )
        self.focus_btn.pack(side="right", padx=(4, 0))

        self.f1_btn = tk.Button(
            row3,
            text="🔴 Red Light (F1)",
            bg="#DC2626",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=2,
            command=self._handle_red_light,
        )
        self.f1_btn.pack(side="right", padx=(4, 4))

    def _browse_exe(self):
        f = filedialog.askopenfilename(
            title="Select EzCAD Executable (EzCad2.exe)",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")],
        )
        if f:
            self.exe_var.set(f)

    def _browse_template(self):
        f = filedialog.askopenfilename(
            title="Select EzCAD Template (.ezd)",
            filetypes=[("EzCAD Template Files", "*.ezd"), ("All Files", "*.*")],
        )
        if f:
            self.template_var.set(f)

    def _browse_input_file(self):
        f = filedialog.askopenfilename(
            title="Select Laser Input Text File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if f:
            self.input_file_var.set(f)

    def _open_input_file(self):
        path = self.get_input_file_path()
        if os.path.isfile(path):
            try:
                os.startfile(path)
            except Exception:
                subprocess.Popen(["notepad.exe", path])

    def _handle_sim_toggle(self):
        if self.on_simulation_toggle:
            self.on_simulation_toggle(self.sim_var.get())

    def _handle_launch_focus(self):
        if self.on_launch_ezcad:
            self.on_launch_ezcad()

    def _handle_red_light(self):
        if self.on_red_light:
            self.on_red_light()

    def get_ezcad_exe_path(self) -> str:
        return self.exe_var.get().strip()

    def get_template_path(self) -> str:
        return self.template_var.get().strip()

    def get_input_file_path(self) -> str:
        return self.input_file_var.get().strip()

    def get_mark_delay(self) -> float:
        try:
            return max(float(self.delay_var.get()), 0.3)
        except ValueError:
            return 1.5

    def is_simulation(self) -> bool:
        return self.sim_var.get()

    def set_simulation(self, sim: bool):
        self.sim_var.set(sim)
