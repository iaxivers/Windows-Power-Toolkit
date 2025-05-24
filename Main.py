import sys
import os
import subprocess
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from pages.home_page        import HomePage
from pages.storage_page     import StoragePage
from pages.network_page     import NetworkPage
from pages.system_info_page import SystemInfoPage
from pages.help_page        import HelpPage

class PowerToolkitApp(tb.Window):
    def __init__(self):
        super().__init__(
            title="Windows Power Toolkit",
            themename="flatly",
            minsize=(1000, 700)
        )
        self._build_ui()

    def _build_ui(self):
        container = tb.Frame(self)
        container.pack(fill=BOTH, expand=YES)

        sidebar = tb.Frame(container, width=180, bootstyle="light")
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        content = tb.Frame(container)
        content.pack(side=RIGHT, fill=BOTH, expand=YES)

        # instantiate pages
        self.pages = {}
        home = HomePage(content, help_callback=lambda: self.show_page("Help"))
        home.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.pages["Home"] = home
        for PageClass, name in [
            (StoragePage,    "Storage"),
            (NetworkPage,    "Network"),
            (SystemInfoPage, "System Info"),
            (HelpPage,       "Help"),
        ]:
            p = PageClass(content)
            p.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.pages[name] = p

        # Introduction box
        intro_frame = tk.Frame(sidebar, bd=1, relief="solid")
        intro_frame.pack(fill=X, pady=(10,2), padx=5)
        tk.Label(
            intro_frame,
            text="Introduction",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            fg="black",
            bg=intro_frame.cget("bg")
        ).pack(fill=X, padx=5, pady=(4,2))
        for name in ["Home", "Help"]:
            tb.Button(
                intro_frame,
                text=name,
                bootstyle="secondary",
                width=16,
                command=lambda n=name: self.show_page(n)
            ).pack(fill=X, pady=2, padx=5)

        # Tools box
        tools_frame = tk.Frame(sidebar, bd=1, relief="solid")
        tools_frame.pack(fill=X, pady=(10,2), padx=5)
        tk.Label(
            tools_frame,
            text="Tools",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            fg="black",
            bg=tools_frame.cget("bg")
        ).pack(fill=X, padx=5, pady=(4,2))
        for name in ["Storage", "Network", "System Info"]:
            tb.Button(
                tools_frame,
                text=name,
                bootstyle="secondary",
                width=16,
                command=lambda n=name: self.show_page(n)
            ).pack(fill=X, pady=2, padx=5)

        # Utilities box
        util_frame = tk.Frame(sidebar, bd=1, relief="solid")
        util_frame.pack(fill=X, pady=(10,2), padx=5)
        tk.Label(
            util_frame,
            text="Utilities",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
            fg="black",
            bg=util_frame.cget("bg")
        ).pack(fill=X, padx=5, pady=(4,2))

        def launch(exe):
            try:
                os.startfile(exe)
            except OSError:
                subprocess.Popen(f'start {exe}', shell=True)

        for label, exe in [
            ("PowerShell",     "powershell.exe"),
            ("Registry Editor","regedit.exe"),
            ("Command Prompt", "cmd.exe"),
            ("Task Manager",   "taskmgr.exe"),
        ]:
            tb.Button(
                util_frame,
                text=label,
                bootstyle="secondary",
                width=16,
                command=lambda e=exe: launch(e)
            ).pack(fill=X, pady=2, padx=5)

        # show Home on launch
        self.show_page("Home")

    def show_page(self, name):
        for p in self.pages.values():
            p.lower()
        self.pages[name].lift()

if __name__ == "__main__":
    app = PowerToolkitApp()
    app.mainloop()
