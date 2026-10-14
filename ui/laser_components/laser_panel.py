"""EzCAD laser marking configuration and control panel with hardware feedback."""

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable, Optional


class LaserPanel(ttk.LabelFrame):
    """Panel managing EzCAD template configuration, text substitution, and marking commands."""

    def __init__(
        self,
        parent,
        default_template: str,
        default_ezcad_dir: str,
        default_entity: str = "t1",
        default_simulation: bool = False,
        default_auto_mark: bool = False,
        default_continuous: bool = False,
        on_update_template: Optional[Callable[[str, str], None]] = None,
        on_mark: Optional[Callable[[], None]] = None,
        on_read_and_mark: Optional[Callable[[], None]] = None,
        on_stop_mark: Optional[Callable[[], None]] = None,
        on_simulation_toggle: Optional[Callable[[bool], None]] = None,
        on_continuous_toggle: Optional[Callable[[bool, float], None]] = None,
    ):
        super().__init__(parent, text="EzCAD Laser Marking & Feedback Control", padding=(12, 10))
        self.on_update_template = on_update_template
        self.on_mark = on_mark
        self.on_read_and_mark = on_read_and_mark
        self.on_stop_mark = on_stop_mark
        self.on_simulation_toggle = on_simulation_toggle
        self.on_continuous_toggle = on_continuous_toggle

        self.jobs_completed_count = 0

        self.columnconfigure(1, weight=1)

        # Row 0: Template File (.ezd)
        ttk.Label(self, text="Template File:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.template_var = tk.StringVar(value=default_template)
        self.template_entry = ttk.Entry(self, textvariable=self.template_var)
        self.template_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.browse_tmpl_btn = ttk.Button(self, text="Browse...", width=9, command=self._browse_template)
        self.browse_tmpl_btn.grid(row=0, column=2, sticky="e", pady=3)

        # Row 1: EzCAD Directory
        ttk.Label(self, text="EzCAD Path:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.ezcad_var = tk.StringVar(value=default_ezcad_dir)
        self.ezcad_entry = ttk.Entry(self, textvariable=self.ezcad_var)
        self.ezcad_entry.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=3)
        self.browse_dir_btn = ttk.Button(self, text="Browse...", width=9, command=self._browse_ezcad_dir)
        self.browse_dir_btn.grid(row=1, column=2, sticky="e", pady=3)

        # Row 2: Entity Name & Prefix
        row2_frame = ttk.Frame(self)
        row2_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 6))
        row2_frame.columnconfigure(1, weight=1)
        row2_frame.columnconfigure(3, weight=1)

        ttk.Label(row2_frame, text="Entity Name:").grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.entity_var = tk.StringVar(value=default_entity)
        self.entity_entry = ttk.Entry(row2_frame, textvariable=self.entity_var, width=12)
        self.entity_entry.grid(row=0, column=1, sticky="w", padx=(0, 12))

        ttk.Label(row2_frame, text="Tag Prefix:").grid(row=0, column=2, sticky="w", padx=(0, 4))
        self.prefix_var = tk.StringVar(value="")
        self.prefix_entry = ttk.Entry(row2_frame, textvariable=self.prefix_var, width=12)
        self.prefix_entry.grid(row=0, column=3, sticky="w")

        # Row 3: Options (Auto-mark, Continuous loop & Simulation mode)
        row3_frame = ttk.Frame(self)
        row3_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(2, 6))

        self.auto_mark_var = tk.BooleanVar(value=default_auto_mark)
        self.auto_mark_chk = ttk.Checkbutton(
            row3_frame,
            text="Auto-Mark on Read",
            variable=self.auto_mark_var,
        )
        self.auto_mark_chk.pack(side="left", padx=(0, 12))

        self.continuous_var = tk.BooleanVar(value=default_continuous)
        self.continuous_chk = ttk.Checkbutton(
            row3_frame,
            text="Continuous Loop (Auto-Next on Feedback)",
            variable=self.continuous_var,
            command=self._handle_continuous_toggle,
        )
        self.continuous_chk.pack(side="left", padx=(0, 6))

        ttk.Label(row3_frame, text="Delay (s):").pack(side="left", padx=(0, 2))
        self.next_delay_var = tk.DoubleVar(value=1.0)
        self.next_delay_entry = ttk.Entry(row3_frame, textvariable=self.next_delay_var, width=4)
        self.next_delay_entry.pack(side="left", padx=(0, 12))

        self.sim_var = tk.BooleanVar(value=default_simulation)
        self.sim_chk = ttk.Checkbutton(
            row3_frame,
            text="Simulation Mode",
            variable=self.sim_var,
            command=self._handle_sim_toggle,
        )
        self.sim_chk.pack(side="left")

        # Row 4: Action Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 4))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=2)
        btn_frame.columnconfigure(3, weight=1)

        self.update_btn = tk.Button(
            btn_frame,
            text="✍ Update Template",
            bg="#3B82F6",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            command=self._handle_update,
        )
        self.update_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.mark_btn = tk.Button(
            btn_frame,
            text="⚡ Mark Tag",
            bg="#D97706",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=10,
            pady=4,
            command=self._handle_mark,
        )
        self.mark_btn.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        self.read_mark_btn = tk.Button(
            btn_frame,
            text="🚀 READ & MARK (AUTO-FLOW)",
            bg="#7C3AED",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="raised",
            padx=12,
            pady=6,
            command=self._handle_read_and_mark,
        )
        self.read_mark_btn.grid(row=0, column=2, sticky="ew", padx=(0, 4))

        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ Stop Laser",
            bg="#EF4444",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="raised",
            padx=8,
            pady=4,
            command=self._handle_stop,
        )
        self.stop_btn.grid(row=0, column=3, sticky="ew")

        # Row 5: Live Hardware Feedback & Status Indicator
        feedback_frame = ttk.Frame(self)
        feedback_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 2))
        feedback_frame.columnconfigure(0, weight=2)
        feedback_frame.columnconfigure(1, weight=1)

        self.status_banner = tk.Label(
            feedback_frame,
            text="● LASER READY (WAITING FOR JOB)",
            font=("Segoe UI", 9, "bold"),
            bg="#DCFCE7",
            fg="#166534",
            padx=10,
            pady=5,
            relief="groove",
            borderwidth=1,
            anchor="w",
        )
        self.status_banner.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.counter_lbl = tk.Label(
            feedback_frame,
            text="Jobs Marked: 0",
            font=("Segoe UI", 9, "bold"),
            bg="#F3F4F6",
            fg="#1F2937",
            padx=8,
            pady=5,
            relief="groove",
            borderwidth=1,
        )
        self.counter_lbl.grid(row=0, column=1, sticky="ew")

    def _browse_template(self):
        file_path = filedialog.askopenfilename(
            title="Select EzCAD Template (.ezd)",
            filetypes=[("EzCAD Template Files", "*.ezd"), ("All Files", "*.*")],
        )
        if file_path:
            self.template_var.set(file_path)

    def _browse_ezcad_dir(self):
        dir_path = filedialog.askdirectory(title="Select EzCAD 2.14.11 Directory")
        if dir_path:
            self.ezcad_var.set(dir_path)

    def _handle_sim_toggle(self):
        if self.on_simulation_toggle:
            self.on_simulation_toggle(self.sim_var.get())

    def _handle_continuous_toggle(self):
        active = self.continuous_var.get()
        delay = self.get_next_job_delay()
        if self.on_continuous_toggle:
            self.on_continuous_toggle(active, delay)

    def _handle_update(self):
        if self.on_update_template:
            entity = self.entity_var.get().strip() or "t1"
            prefix = self.prefix_var.get().strip()
            self.on_update_template(entity, prefix)

    def _handle_mark(self):
        if self.on_mark:
            self.on_mark()

    def _handle_read_and_mark(self):
        if self.on_read_and_mark:
            self.on_read_and_mark()

    def _handle_stop(self):
        if self.on_stop_mark:
            self.on_stop_mark()

    def get_template_path(self) -> str:
        return self.template_var.get().strip()

    def get_ezcad_dir(self) -> str:
        return self.ezcad_var.get().strip()

    def get_entity_name(self) -> str:
        return self.entity_var.get().strip() or "t1"

    def get_prefix(self) -> str:
        return self.prefix_var.get().strip()

    def is_auto_mark_enabled(self) -> bool:
        return self.auto_mark_var.get()

    def is_continuous_enabled(self) -> bool:
        return self.continuous_var.get()

    def get_next_job_delay(self) -> float:
        try:
            val = float(self.next_delay_var.get())
            return max(val, 0.2)
        except ValueError:
            return 1.0

    def is_simulation(self) -> bool:
        return self.sim_var.get()

    def set_simulation(self, sim: bool) -> None:
        self.sim_var.set(sim)

    def set_marking_state(self, is_marking: bool, status_msg: str = "", level: str = "INFO"):
        """Update buttons and live status feedback banner."""
        if is_marking:
            self.mark_btn.config(state="disabled", text="Marking...")
            self.read_mark_btn.config(state="disabled")
            self.update_btn.config(state="disabled")
            self.status_banner.config(
                text=status_msg or "⏳ LASER MARKING IN PROGRESS... WAITING FOR COMPLETION",
                bg="#FEF3C7",
                fg="#92400E",
            )
        else:
            self.mark_btn.config(state="normal", text="⚡ Mark Tag")
            self.read_mark_btn.config(state="normal")
            self.update_btn.config(state="normal")
            if level == "SUCCESS":
                self.status_banner.config(
                    text=status_msg or "✅ JOB DONE (FEEDBACK: OK) — READY FOR NEXT",
                    bg="#DCFCE7",
                    fg="#166534",
                )
            elif level == "ERROR":
                self.status_banner.config(
                    text=status_msg or "❌ MARKING FAILED",
                    bg="#FEE2E2",
                    fg="#991B1B",
                )
            else:
                self.status_banner.config(
                    text="● LASER READY (WAITING FOR JOB)",
                    bg="#DCFCE7",
                    fg="#166534",
                )

    def record_job_completed(self, duration: float):
        """Increment counter and display last job duration."""
        self.jobs_completed_count += 1
        self.counter_lbl.config(
            text=f"Jobs Marked: {self.jobs_completed_count} ({duration:.2f}s)"
        )
