import ttkbootstrap as tb
from ttkbootstrap.constants import *

class HomePage(tb.Frame):
    def __init__(self, master, help_callback):
        super().__init__(master)
        self.help_callback = help_callback

        tb.Label(
            self,
            text="Windows Power Toolkit",
            font=("Segoe UI", 24, "bold")
        ).pack(pady=(30, 10))

        tb.Label(
            self,
            text="Version 1.0.0    •    Made by Iaxivers",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 20))

        desc = (
            "Windows Power Toolkit is a single GUI for key Windows tools.\n"
            "Run diagnostics, network tests, and storage scans in one place.\n"
            "View system info and explore Windows internals easier than ever before.\n"
            "Built for power users, sysadmins, and engineers.\n\n"

        )
        tb.Label(
            self,
            text=desc,
            font=("Segoe UI", 12),
            justify="center"
        ).pack(pady=(0, 30))

        tb.Button(
            self,
            text="View Help",
            bootstyle="secondary",
            command=self.help_callback
        ).pack(pady=(0, 40))
