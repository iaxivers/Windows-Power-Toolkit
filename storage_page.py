# pages/storage_page.py

import os
import hashlib
import tempfile
import datetime
import subprocess
import threading
import ctypes
import textwrap
import shutil
import glob

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog

import psutil
import wmi
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class TaskWindow(tk.Toplevel):
    def __init__(self, title: str, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("400x110")
        self.resizable(False, False)
        self.progress = tb.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill=X, padx=20, pady=(18, 5))
        self.status = tb.Label(self, text="Starting …")
        self.status.pack(fill=X, padx=20)

    def start(self, fn, args: tuple = ()) -> None:
        self.progress.start()
        threading.Thread(target=self._run, args=(fn, args), daemon=True).start()

    def _run(self, fn, args):
        try:
            fn(*args, status_cb=self._update_status)
            self._finish()
        except Exception as exc:
            self._finish_error(exc)

    def _safe(self, call, *a, **kw):
        try:
            call(*a, **kw)
        except tk.TclError:
            pass

    def _update_status(self, msg: str) -> None:
        self.after(0, lambda m=msg: self._safe(self.status.config, text=m))

    def _finish(self) -> None:
        self.after(0, lambda: self._safe(self.progress.stop))
        self.after(0, lambda: self._safe(self.status.config, text="Done"))

    def _finish_error(self, err: Exception) -> None:
        self.after(0, lambda: self._safe(self.progress.stop))
        self.after(0, lambda: self._safe(self.status.config, text=f"Error: {err}"))

class StoragePage(tb.Frame):
    def __init__(self, master: tk.Misc):
        super().__init__(master)

        pad = dict(padx=10, pady=8)
        tb.Label(self, text="Storage Utilities", font=(None, 16, "bold")).pack(anchor="w", **pad)

        try:
            self.winfo_toplevel().geometry("1200x800")
        except Exception:
            pass

        self.active_tree: tb.Treeview | None = None
        self.unit_var = tk.StringVar(value="MB")

        self._build_header()
        self._build_tabs()
        self.bind_all("<Control-a>", lambda _e: self._select_all())
        self.bind_all("<Control-c>", lambda _e: self._copy_selected())

    def _build_header(self):
        ctl = tb.Frame(self)
        ctl.pack(fill=X, padx=12, pady=6)
        tb.Label(ctl, text="Units:").pack(side=LEFT, padx=(0, 5))
        cb = tb.Combobox(
            ctl, textvariable=self.unit_var,
            values=["KB", "MB", "GB", "TB", "PB"],
            state="readonly", width=6,
        )
        cb.pack(side=LEFT)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_overview())

    def _build_tabs(self):
        nb = tb.Notebook(self)
        nb.pack(fill=BOTH, expand=YES, padx=12, pady=8)
        self._build_overview(nb)
        self._build_speed(nb)
        self._build_mount(nb)
        self._build_format(nb)
        self._build_cleanup(nb)
        self._build_filemgr(nb)
        self._build_robocopy_danger(nb)

    def _select_all(self):
        if self.active_tree:
            self.active_tree.selection_set(self.active_tree.get_children())

    def _copy_selected(self):
        if not self.active_tree:
            return
        paths = [self.active_tree.item(i)["values"][0] for i in self.active_tree.selection()]
        if paths:
            self.clipboard_clear()
            self.clipboard_append("\n".join(paths))
            messagebox.showinfo("Copy", "Copied to clipboard")

    def _on_tree_select(self, tv):
        self.active_tree = tv

    def _make_tree_sortable(self, tv):
        for col in tv["columns"]:
            tv.heading(col, command=lambda c=col, t=tv: self._sort_treeview(t, c, False))

    def _sort_treeview(self, tv, col, reverse):
        data = [(tv.set(k, col), k) for k in tv.get_children("")]
        try:
            data = [(float(v), k) for v, k in data]
        except ValueError:
            pass
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            tv.move(k, "", idx)
        tv.heading(col, command=lambda: self._sort_treeview(tv, col, not reverse))

    def _apply_filter(self, tv, col, pat):
        for iid in tv.get_children():
            tv.reattach(iid, "", "end")
        p = pat.lower()
        if not p:
            return
        for iid in tv.get_children():
            val = tv.set(iid, col).lower()
            if p not in val:
                tv.detach(iid)

    # ------------------ Overview Tab ------------------
    def _build_overview(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Overview")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Shows all mounted drives with total/used/free, type, FS & cluster\n"
                "2) Pie chart shows used vs free\n"
                "3) Click Refresh to update\n"
                "4) Sort by clicking headers"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        chart_box = tb.Labelframe(tab, text="Drive Usage Chart")
        chart_box.pack(fill=X, padx=12, pady=(0, 6))
        fig, ax = plt.subplots(figsize=(4, 1.5))
        self.ov_ax = ax
        self.ov_canvas = FigureCanvasTkAgg(fig, master=chart_box)
        self.ov_canvas.get_tk_widget().pack()

        cols = ("device", "mount", "total", "used", "free", "type", "fs", "cluster")
        tv = tb.Treeview(tab, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            tv.heading(c, text=c.title())
        tv.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        tv.bind("<<TreeviewSelect>>", lambda _e, v=tv: self._on_tree_select(v))
        self.ov_tv = tv
        self._make_tree_sortable(tv)

        btns = tb.Frame(tab)
        btns.pack(fill=X, padx=12, pady=(0, 6))
        tb.Button(btns, text="Refresh", bootstyle=PRIMARY, command=self._ov_refresh).pack(side=LEFT)
        tb.Button(btns, text="Chart",   bootstyle=INFO,    command=self._start_chart).pack(side=LEFT, padx=6)

        self._ov_refresh()

    def _ov_refresh(self):
        self.ov_tv.delete(*self.ov_tv.get_children())
        dev_map = {}
        try:
            cw = wmi.WMI()
            for d in cw.Win32_DiskDrive():
                model = (d.Model or "").lower()
                dtype = "SSD" if ("ssd" in model or "nvme" in model) else "HDD"
                for part in d.associators("Win32_DiskDriveToDiskPartition"):
                    for ld in part.associators("Win32_LogicalDiskToPartition"):
                        dev_map[ld.DeviceID] = dtype
        except Exception:
            pass

        unit = self.unit_var.get()
        factor = {"KB":1024, "MB":1024**2, "GB":1024**3, "TB":1024**4, "PB":1024**5}[unit]

        total_used = total_free = 0
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue
            dev = part.device.rstrip("\\")
            dtype = dev_map.get(dev, "HDD")
            fs, cluster = self._get_fs_cluster(part.mountpoint)
            total_used += usage.used
            total_free += usage.free
            self.ov_tv.insert(
                "", "end",
                values=(
                    part.device,
                    part.mountpoint,
                    f"{usage.total / factor:.1f} {unit}",
                    f"{usage.used / factor:.1f} {unit}",
                    f"{usage.free / factor:.1f} {unit}",
                    dtype,
                    fs,
                    f"{cluster / factor:.1f} {unit}"
                )
            )

        self.ov_ax.clear()
        try:
            self.ov_ax.pie(
                [total_used, total_free],
                labels=["Used", "Free"],
                autopct="%1.0f%%",
                startangle=90
            )
        except Exception:
            pass
        self.ov_canvas.draw()

    def _get_fs_cluster(self, mount: str):
        buf1 = ctypes.create_unicode_buffer(256)
        buf2 = ctypes.create_unicode_buffer(256)
        vs = ctypes.c_uint()
        mc = ctypes.c_uint()
        fl = ctypes.c_uint()
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(mount), buf1, 256,
            ctypes.byref(vs), ctypes.byref(mc),
            ctypes.byref(fl), buf2, 256
        )
        fs = buf2.value or "?"
        spc = ctypes.c_uint()
        bps = ctypes.c_uint()
        ctypes.windll.kernel32.GetDiskFreeSpaceW(
            ctypes.c_wchar_p(mount),
            ctypes.byref(spc), ctypes.byref(bps),
            ctypes.byref(ctypes.c_uint()), ctypes.byref(ctypes.c_uint())
        )
        return fs, spc.value * bps.value

    def _start_chart(self):
        sel = self.ov_tv.selection()
        if not sel:
            return messagebox.showwarning("Chart", "Select a drive")
        mount = self.ov_tv.item(sel[0])["values"][1]
        TaskWindow("Building Chart", self).start(self._chart_worker, (mount,))

    def _chart_worker(self, mount, status_cb):
        status_cb("Scanning folders …")
        data = {}
        for name in os.listdir(mount):
            path = os.path.join(mount, name)
            if not os.path.isdir(path):
                continue
            size = 0
            for r, _, files in os.walk(path):
                for f in files:
                    try:
                        size += os.path.getsize(os.path.join(r, f))
                    except Exception:
                        pass
            data[name] = size

        total = sum(data.values())
        thresh = total * 0.01
        big = {k: v for k, v in data.items() if v >= thresh}
        small = [k for k, v in data.items() if v < thresh]
        items = sorted(big.items(), key=lambda x: x[1], reverse=True)
        top = items[:10]
        other = sum(v for _, v in items[10:]) + sum(data[k] for k in small)
        labels = [k for k, _ in top] + (["Other"] if other else [])
        sizes = [v for _, v in top] + ([other] if other else [])

        status_cb("Rendering chart …")
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct="%1.1f%%")

        def show():
            win = tk.Toplevel(self)
            win.title("Folder Breakdown")
            if small:
                lf = tb.Labelframe(win, text="(<1%) folders:")
                lf.pack(fill=X, padx=12, pady=6)
                tb.Label(lf, text=", ".join(small),
                         wraplength=800, justify=LEFT).pack(fill=X, padx=12)
            canv = FigureCanvasTkAgg(fig, master=win)
            canv.draw()
            canv.get_tk_widget().pack(fill=BOTH, expand=YES)
        self.after(0, show)

    # ------------------ Speed Test Tab ------------------
    def _build_speed(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Speed Test")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Choose a local folder\n"
                "2) Click Run Test to measure write/read speeds\n"
                "3) Progress bar indicates completion"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        frm = tb.Frame(tab)
        frm.pack(fill=X, padx=12, pady=6)
        tb.Label(frm, text="Folder:").pack(side=LEFT, padx=5)
        self.speed_lbl = tb.Label(frm, text="(none)")
        self.speed_lbl.pack(side=LEFT, padx=5)
        tb.Button(frm, text="Choose …", bootstyle=SECONDARY,
                  command=self._choose_speed_folder).pack(side=LEFT, padx=5)

        self.speed_bar = tb.Progressbar(tab, mode="determinate", length=400)
        self.speed_bar.pack(padx=5, pady=10)
        tb.Button(tab, text="Run Test", bootstyle=PRIMARY,
                  command=self._run_speed_test).pack(pady=5)
        tb.Label(tab, text="Tip: use a local (non-USB) folder").pack()

    def _choose_speed_folder(self):
        d = filedialog.askdirectory()
        if d:
            self.speed_dir = d
            self.speed_lbl.configure(text=d)

    def _run_speed_test(self):
        folder = getattr(self, "speed_dir", tempfile.gettempdir())
        fname = os.path.join(folder, "speedtest.tmp")
        total, chunk = 50 * 1024**2, 1 * 1024**2
        self.speed_bar["maximum"] = total
        self.speed_bar["value"] = 0

        try:
            st = datetime.datetime.now()
            with open(fname, "wb") as f:
                w = 0
                while w < total:
                    f.write(b"\0" * chunk)
                    w += chunk
                    self.speed_bar["value"] = w
                    self.speed_bar.update()
            wtime = (datetime.datetime.now() - st).total_seconds()
        except PermissionError:
            return messagebox.showerror("Speed", "No write permission")

        st2 = datetime.datetime.now()
        with open(fname, "rb") as f:
            while f.read(chunk):
                pass
        rtime = (datetime.datetime.now() - st2).total_seconds()

        try:
            os.remove(fname)
        except Exception:
            pass

        mb = total / 1024**2
        messagebox.showinfo(
            "Results",
            f"Write: {mb / max(wtime,0.001):.1f} MB/s\nRead : {mb / max(rtime,0.001):.1f} MB/s"
        )

    # ------------------ Unmount/Eject/ISO Tab ------------------
    def _build_mount(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Unmount / Eject / ISO")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Select drive and click Unmount or Eject\n"
                "2) For ISO, browse to .iso then Mount or Dismount\n"
                "3) Eject powers off removable media"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        frm = tb.Frame(tab)
        frm.pack(fill=X, padx=12, pady=6)
        tb.Label(frm, text="Drive:").pack(side=LEFT, padx=5)
        vals = [p.device.rstrip("\\") for p in psutil.disk_partitions(all=False)]
        self.mount_vol = tb.Combobox(frm, values=vals, width=10)
        if vals:
            self.mount_vol.current(0)
        self.mount_vol.pack(side=LEFT, padx=5)
        tb.Button(frm, text="Unmount", bootstyle=WARNING,
                  command=self._dismount).pack(side=LEFT, padx=5)
        tb.Button(frm, text="Eject", bootstyle=DANGER,
                  command=self._eject).pack(side=LEFT, padx=5)

        iso_frm = tb.Labelframe(tab, text="ISO")
        iso_frm.pack(fill=X, padx=12, pady=6)
        tb.Label(iso_frm, text="Attach / detach ISO files").pack(fill=X, pady=(0,4))
        self.iso_path = tk.StringVar()
        tb.Entry(iso_frm, textvariable=self.iso_path, width=40).pack(side=LEFT, padx=5)
        tb.Button(
            iso_frm, text="Browse …", bootstyle=SECONDARY,
            command=lambda: self.iso_path.set(
                filedialog.askopenfilename(filetypes=[("ISO","*.iso")])
            ),
        ).pack(side=LEFT)
        tb.Button(iso_frm, text="Mount",
                  bootstyle=PRIMARY, command=self._mount_iso).pack(side=LEFT, padx=5)
        tb.Button(iso_frm, text="Dismount",
                  bootstyle=WARNING, command=self._dismount_iso).pack(side=LEFT, padx=5)

    def _dismount(self):
        d = self.mount_vol.get()
        if not d:
            return
        if messagebox.askyesno("Unmount", f"Unmount {d}?"):
            try:
                for vol in wmi.WMI().Win32_Volume(DriveLetter=f"{d}:"):
                    vol.Dismount(True, False)
                messagebox.showinfo("Unmount", f"{d} unmounted")
            except Exception:
                messagebox.showerror("Unmount", "Failed")

    def _eject(self):
        d = self.mount_vol.get()
        if not d:
            return
        if messagebox.askyesno("Eject", f"Eject {d}?"):
            ok = False
            cw = wmi.WMI()
            for vol in cw.Win32_Volume(DriveLetter=f"{d}:"):
                if vol.Eject() == 0:
                    ok = True
            if not ok:
                subprocess.run(
                    [
                        "powershell","-NoProfile","-Command",
                        "(New-Object -ComObject Shell.Application)"
                        f".Namespace(17).ParseName('{d}').InvokeVerb('Eject')"
                    ],
                    shell=True
                )
            messagebox.showinfo("Eject", f"{d} ejected")

    def _mount_iso(self):
        iso = self.iso_path.get()
        if not iso:
            return messagebox.showwarning("Mount ISO","Pick an ISO file")
        try:
            subprocess.run(
                ["powershell","-NoProfile","-Command",
                 f"Mount-DiskImage -ImagePath '{iso}'"],
                shell=True, check=True
            )
            messagebox.showinfo("Mount ISO","Mounted")
            self._ov_refresh()
        except Exception:
            messagebox.showerror("Mount ISO","Failed")

    def _dismount_iso(self):
        iso = self.iso_path.get()
        if not iso:
            return messagebox.showwarning("Dismount ISO","Pick an ISO file")
        try:
            subprocess.run(
                ["powershell","-NoProfile","-Command",
                 f"Dismount-DiskImage -ImagePath '{iso}'"],
                shell=True, check=True
            )
            messagebox.showinfo("Dismount ISO","Done")
            self._ov_refresh()
        except Exception:
            messagebox.showerror("Dismount ISO","Failed")

    # ------------------ Format Tab ------------------
    def _build_format(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Format")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Select drive and filesystem type\n"
                "2) Click Format — ALL DATA WILL BE ERASED\n"
                "3) Wait for completion"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        frm = tb.Frame(tab); frm.pack(fill=X, padx=12, pady=6)
        tb.Label(frm, text="Drive:").pack(side=LEFT, padx=5)
        vals = [p.device.rstrip("\\") for p in psutil.disk_partitions(all=False)]
        self.fmt_vol = tb.Combobox(frm, values=vals, width=10)
        if vals:
            self.fmt_vol.current(0)
        self.fmt_vol.pack(side=LEFT, padx=5)
        tb.Label(frm, text="FS:").pack(side=LEFT, padx=5)
        self.fmt_fs = tb.Combobox(frm, values=["NTFS","FAT32","exFAT"], width=8)
        self.fmt_fs.current(0)
        self.fmt_fs.pack(side=LEFT, padx=5)
        tb.Button(tab, text="Format", bootstyle=DANGER, command=self._format).pack(pady=10)

    def _format(self):
        v, fs = self.fmt_vol.get(), self.fmt_fs.get()
        if not v:
            return
        if not messagebox.askyesno("Format", f"Erase ALL data on {v}?"):
            return
        try:
            subprocess.run(
                ["powershell","-NoProfile","-Command",
                 f"Format-Volume -DriveLetter {v} -FileSystem {fs} -Confirm:$false -Force"],
                shell=True, check=True
            )
            messagebox.showinfo("Format", f"Formatted {v} as {fs}")
            self._ov_refresh()
        except Exception as exc:
            messagebox.showerror("Format", f"Failed: {exc}")

    def _refresh_overview(self):
        self._ov_refresh()

    # ------------------ Cleanup Tab ------------------
    def _build_cleanup(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Cleanup")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Choose sub-tab\n"
                "2) List items\n"
                "3) Delete selected or all"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        cleanup_nb = tb.Notebook(tab)
        cleanup_nb.pack(fill=BOTH, expand=YES, padx=8, pady=8)
        self._build_temp_tab(cleanup_nb)
        self._build_recycle_tab(cleanup_nb)
        self._build_browser_tab(cleanup_nb)
        self._build_win_cache_tab(cleanup_nb)

    def _build_temp_tab(self, cleanup_nb):
        f = tb.Frame(cleanup_nb); cleanup_nb.add(f, text="Temp Files")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) List Temp folder\n"
                "2) Delete All to clear\n"
                "3) Ctrl+A to select all, Ctrl+C to copy paths"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        tree = tb.Treeview(f, columns=("file",), show="headings", selectmode="extended")
        tree.heading("file", text="Temp File/Folder")
        tree.pack(fill=BOTH, expand=YES, padx=12, pady=8)
        btns = tb.Frame(f); btns.pack()
        tb.Button(btns, text="List Files", bootstyle=PRIMARY, command=lambda: self._refresh_temp_tree(tree)).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Delete All", bootstyle=DANGER, command=lambda: self._delete_temp(tree)).pack(side=LEFT, padx=6)
        self._refresh_temp_tree(tree)

    def _refresh_temp_tree(self, tree):
        tree.delete(*tree.get_children())
        tempdir = tempfile.gettempdir()
        for name in os.listdir(tempdir):
            tree.insert("", "end", values=(os.path.join(tempdir, name),))

    def _delete_temp(self, tree):
        tempdir = tempfile.gettempdir()
        if not messagebox.askyesno("Delete Temp", f"Delete everything in {tempdir}?"):
            return
        count = 0
        for name in os.listdir(tempdir):
            path = os.path.join(tempdir, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
                count += 1
            except Exception:
                pass
        messagebox.showinfo("Temp Files", f"Deleted {count} items.")
        self._refresh_temp_tree(tree)

    def _build_recycle_tab(self, cleanup_nb):
        f = tb.Frame(cleanup_nb); cleanup_nb.add(f, text="Recycle Bin")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) List Recycle Bin\n"
                "2) Empty Bin to clear"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        tree = tb.Treeview(f, columns=("file",), show="headings", selectmode="extended")
        tree.heading("file", text="Recycled Item")
        tree.pack(fill=BOTH, expand=YES, padx=12, pady=8)
        btns = tb.Frame(f); btns.pack()
        tb.Button(btns, text="List Files", bootstyle=PRIMARY, command=lambda: self._refresh_recycle_tree(tree)).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Empty Bin", bootstyle=DANGER, command=lambda: self._delete_recycle(tree)).pack(side=LEFT, padx=6)
        self._refresh_recycle_tree(tree)

    def _refresh_recycle_tree(self, tree):
        tree.delete(*tree.get_children())
        if send2trash is None:
            tree.insert("", "end", values=("Install send2trash",))
            return
        import winshell
        try:
            for item in winshell.recycle_bin():
                tree.insert("", "end", values=(item.filename,))
        except Exception as ex:
            tree.insert("", "end", values=(str(ex),))

    def _delete_recycle(self, tree):
        if send2trash is None:
            messagebox.showwarning("Recycle Bin", "send2trash not installed")
            return
        import winshell
        if not messagebox.askyesno("Recycle Bin", "Empty the entire Recycle Bin?"):
            return
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        messagebox.showinfo("Recycle Bin", "Emptied.")
        self._refresh_recycle_tree(tree)

    def _build_browser_tab(self, cleanup_nb):
        f = tb.Frame(cleanup_nb); cleanup_nb.add(f, text="Browser Cache")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) List browser caches\n"
                "2) Delete All to clear"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        tree = tb.Treeview(f, columns=("file",), show="headings", selectmode="extended")
        tree.heading("file", text="Cache Path")
        tree.pack(fill=BOTH, expand=YES, padx=12, pady=8)
        btns = tb.Frame(f); btns.pack()
        tb.Button(btns, text="List Cache", bootstyle=PRIMARY, command=lambda: self._refresh_browser_tree(tree)).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Delete All", bootstyle=DANGER, command=lambda: self._delete_browser_cache(tree)).pack(side=LEFT, padx=6)
        self._refresh_browser_tree(tree)

    def _browser_cache_paths(self):
        local = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")
        paths = []
        chrome = os.path.join(local,"Google","Chrome","User Data","Default","Cache")
        if os.path.isdir(chrome): paths.append(chrome)
        edge = os.path.join(local,"Microsoft","Edge","User Data","Default","Cache")
        if os.path.isdir(edge): paths.append(edge)
        for d in glob.glob(os.path.join(appdata,"Mozilla","Firefox","Profiles","*")):
            c2 = os.path.join(d,"cache2")
            if os.path.isdir(c2): paths.append(c2)
        return paths

    def _refresh_browser_tree(self, tree):
        tree.delete(*tree.get_children())
        for p in self._browser_cache_paths():
            tree.insert("", "end", values=(p,))

    def _delete_browser_cache(self, tree):
        paths = self._browser_cache_paths()
        if not paths:
            messagebox.showinfo("Browser Cache","No cache found.")
            return
        if not messagebox.askyesno("Browser Cache","Delete all?"):
            return
        for p in paths:
            shutil.rmtree(p, ignore_errors=True)
        messagebox.showinfo("Browser Cache","Deleted cache.")
        self._refresh_browser_tree(tree)

    def _build_win_cache_tab(self, cleanup_nb):
        f = tb.Frame(cleanup_nb); cleanup_nb.add(f, text="Windows Cache")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) List Windows cache folders\n"
                "2) Delete All to clear"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        tree = tb.Treeview(f, columns=("file",), show="headings", selectmode="extended")
        tree.heading("file", text="Cache Path")
        tree.pack(fill=BOTH, expand=YES, padx=12, pady=8)
        btns = tb.Frame(f); btns.pack()
        tb.Button(btns, text="List Cache", bootstyle=PRIMARY, command=lambda: self._refresh_win_cache_tree(tree)).pack(side=LEFT, padx=6)
        tb.Button(btns, text="Delete All", bootstyle=DANGER, command=lambda: self._delete_win_cache(tree)).pack(side=LEFT, padx=6)
        self._refresh_win_cache_tree(tree)

    def _win_cache_paths(self):
        local = os.environ.get("LOCALAPPDATA","")
        appdata = os.environ.get("APPDATA","")
        windir = os.environ.get("WINDIR","C:\\Windows")
        paths = [
            os.path.join(local,"Microsoft","Windows","INetCache"),
            os.path.join(local,"Microsoft","Windows","WebCache"),
            os.path.join(local,"Microsoft","Windows","Explorer","IconCache"),
            os.path.join(local,"Microsoft","Windows","Explorer","ThumbCache"),
            os.path.join(windir,"Temp"),
            os.path.join(local,"Temp")
        ]
        return [p for p in paths if os.path.exists(p)]

    def _refresh_win_cache_tree(self, tree):
        tree.delete(*tree.get_children())
        for p in self._win_cache_paths():
            tree.insert("", "end", values=(p,))

    def _delete_win_cache(self, tree):
        paths = self._win_cache_paths()
        if not paths:
            messagebox.showinfo("Windows Cache","No cache found.")
            return
        if not messagebox.askyesno("Windows Cache","Delete all?"):
            return
        for p in paths:
            shutil.rmtree(p, ignore_errors=True)
        messagebox.showinfo("Windows Cache","Deleted cache.")
        self._refresh_win_cache_tree(tree)

    # ------------------ FILE MANAGER Tab ------------------
    def _build_filemgr(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="File Manager")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Pick a folder\n"
                "2) Use Search, Duplicates, Empty Folders or Checksums\n"
                "3) Double-click to open"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        fm = tb.Notebook(tab)
        fm.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        self._build_search_tab(fm)
        self._build_duplicates_tab(fm)
        self._build_empty_folders_tab(fm)
        self._build_checksum_tab(fm)

        btn_frame = tb.Frame(tab)
        btn_frame.pack(fill=X, padx=12, pady=(0,6))
        tb.Button(
            btn_frame,
            text="Delete Selected",
            bootstyle=DANGER,
            command=self._delete_selected_filemgr
        ).pack(side=LEFT)

    def _delete_selected_filemgr(self):
        tv = self.active_tree
        if not tv:
            return messagebox.showwarning("Delete","No item selected")
        sel = tv.selection()
        if not sel:
            return messagebox.showwarning("Delete","No item selected")
        paths = []
        for iid in sel:
            vals = tv.item(iid).get("values", [])
            p = vals[0] if os.path.exists(vals[0]) else (vals[1] if len(vals)>1 and os.path.exists(vals[1]) else None)
            if p:
                paths.append(p)
        if not paths:
            return messagebox.showwarning("Delete","No valid items")
        if not messagebox.askyesno("Delete", "Delete these?\n\n"+ "\n".join(paths)):
            return
        for p in paths:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                messagebox.showerror("Delete", f"Failed: {p}\n{e}")
        for iid in sel:
            tv.delete(iid)
        messagebox.showinfo("Delete","Deleted selected items")

    # --- Search sub-tab
    def _build_search_tab(self, fm):
        f = tb.Frame(fm); fm.add(f, text="Search")

        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Click Folder…\n"
                "2) Type to filter\n"
                "3) Double-click to open"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        sf = tb.Frame(f); sf.pack(fill=X, padx=12, pady=6)
        tb.Button(sf, text="Folder…", bootstyle=SECONDARY, command=lambda: self._set_dir("search_dir", sf)).pack(side=LEFT, padx=5)
        self.search_lbl = tb.Label(sf, text="(none)")
        self.search_lbl.pack(side=LEFT, padx=5)
        self.search_pat = tk.Entry(sf)
        self.search_pat.pack(side=LEFT, fill=X, expand=YES, padx=5)
        self.search_pat.bind("<KeyRelease>", lambda _e: self._apply_filter(self.search_tv, "path", self.search_pat.get()))
        tb.Button(sf, text="Go", bootstyle=PRIMARY, command=self._do_search).pack(side=LEFT, padx=5)

        cols = ("path","type","size","modified")
        tv = tb.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            tv.heading(c, text=c.title())
        tv.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        tv.bind("<<TreeviewSelect>>", lambda _e, v=tv: self._on_tree_select(v))
        tv.bind("<Double-1>", lambda _e: os.startfile(tv.item(tv.selection()[0])["values"][0]) if tv.selection() else None)
        self.search_tv = tv
        self._make_tree_sortable(tv)

    def _set_dir(self, attr, frame):
        d = filedialog.askdirectory()
        if not d:
            return
        setattr(self, attr, d)
        getattr(self, attr.replace("_dir","_lbl")).config(text=d)

    def _do_search(self):
        root = getattr(self, "search_dir", None)
        if not root:
            return messagebox.showwarning("Search","Pick a folder first")
        TaskWindow("Searching …", self).start(self._search_worker, (root,))

    def _search_worker(self, root, status_cb):
        tv = self.search_tv
        factor = {"KB":1024,"MB":1024**2,"GB":1024**3,"TB":1024**4,"PB":1024**5}[self.unit_var.get()]
        self.after(0, lambda: tv.delete(*tv.get_children()))
        for base, dirs, files in os.walk(root):
            status_cb(f"Scanning {base} …")
            for nm in dirs+files:
                if self.search_pat.get().strip().lower() not in nm.lower():
                    continue
                p = os.path.join(base, nm)
                try:
                    sz = os.path.getsize(p)/factor
                    m = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d")
                except Exception:
                    sz, m = 0, ""
                typ = "DIR" if os.path.isdir(p) else "FILE"
                self.after(0, lambda r=(p, typ, f"{sz:.1f}", m): tv.insert("", "end", values=r))
        status_cb("Done")

    # --- Duplicates sub-tab
    def _build_duplicates_tab(self, fm):
        f = tb.Frame(fm); fm.add(f, text="Duplicates")

        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Click Folder…\n"
                "2) Click Scan\n"
                "3) Double-click to open"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        sf = tb.Frame(f); sf.pack(fill=X, padx=12, pady=6)
        tb.Button(sf, text="Folder…", bootstyle=SECONDARY, command=lambda: self._set_dir("dupes_dir", sf)).pack(side=LEFT, padx=5)
        self.dupes_lbl = tb.Label(sf, text="(none)")
        self.dupes_lbl.pack(side=LEFT, padx=5)
        tb.Button(sf, text="Scan", bootstyle=PRIMARY, command=self._do_duplicates).pack(side=LEFT, padx=5)

        cols = ("file","size","count")
        tv = tb.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            tv.heading(c, text=c.title())
        tv.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        tv.bind("<<TreeviewSelect>>", lambda _e, v=tv: self._on_tree_select(v))
        tv.bind("<Double-1>", lambda _e: os.startfile(tv.item(tv.selection()[0])["values"][0]) if tv.selection() else None)
        self.dupes_tv = tv
        self._make_tree_sortable(tv)

    def _do_duplicates(self):
        root = getattr(self, "dupes_dir", None)
        if not root:
            return messagebox.showwarning("Duplicates","Pick a folder")
        TaskWindow("Duplicates", self).start(self._dupe_worker, (root,))

    def _dupe_worker(self, root, status_cb):
        status_cb("Scanning sizes …")
        sizes = {}
        for base, _, files in os.walk(root):
            for fn in files:
                p = os.path.join(base, fn)
                try:
                    sz = os.path.getsize(p)
                except Exception:
                    continue
                sizes.setdefault(sz, []).append(p)
        tv = self.dupes_tv
        self.after(0, lambda: tv.delete(*tv.get_children()))
        status_cb("Filtering …")
        for sz, grp in sizes.items():
            if len(grp) < 2:
                continue
            for p in grp:
                self.after(0, lambda r=(p, f"{sz/1024**2:.1f}", len(grp)): tv.insert("", "end", values=r))
        status_cb("Done")

    # --- Empty Folders sub-tab
    def _build_empty_folders_tab(self, fm):
        f = tb.Frame(fm); fm.add(f, text="Empty Folders")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Click Folder…\n"
                "2) Click Scan\n"
                "3) Double-click to open"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        sf = tb.Frame(f); sf.pack(fill=X, padx=12, pady=6)
        tb.Button(sf, text="Folder…", bootstyle=SECONDARY, command=lambda: self._set_dir("empty_dir", sf)).pack(side=LEFT, padx=5)
        self.empty_lbl = tb.Label(sf, text="(none)")
        self.empty_lbl.pack(side=LEFT, padx=5)
        tb.Button(sf, text="Scan", bootstyle=PRIMARY, command=self._do_empty_scan).pack(side=LEFT, padx=5)

        cols = ("folder","path")
        tv = tb.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            tv.heading(c, text=c.title())
        tv.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        tv
        tv.bind("<<TreeviewSelect>>", lambda _e, v=tv: self._on_tree_select(v))
        tv.bind("<Double-1>", lambda _e: os.startfile(tv.item(tv.selection()[0])["values"][1]) if tv.selection() else None)
        self.empty_tv = tv
        self._make_tree_sortable(tv)

    def _do_empty_scan(self):
        root = getattr(self, "empty_dir", None)
        if not root:
            return messagebox.showwarning("Empty Folders","Pick a folder")
        TaskWindow("Empty Folders", self).start(self._empty_worker, (root,))

    def _empty_worker(self, root, status_cb):
        tv = self.empty_tv
        self.after(0, lambda: tv.delete(*tv.get_children()))
        status_cb("Walking …")
        for base, dirs, _ in os.walk(root):
            for d in dirs:
                p = os.path.join(base, d)
                try:
                    if not os.listdir(p):
                        self.after(0, lambda r=(d, p): tv.insert("", "end", values=r))
                except Exception:
                    pass
        status_cb("Done")

    # --- Checksums sub-tab
    def _build_checksum_tab(self, fm):
        f = tb.Frame(fm); fm.add(f, text="Checksums")
        tut = tb.Labelframe(f, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Click Files… or Folder…\n"
                "2) Click MD5 or SHA1\n"
                "3) Double-click to open"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)
        sf = tb.Frame(f); sf.pack(fill=X, padx=12, pady=6)
        tb.Button(sf, text="Files…", bootstyle=SECONDARY, command=self._pick_checksum_files).pack(side=LEFT, padx=5)
        tb.Button(sf, text="Folder…", bootstyle=SECONDARY, command=self._pick_checksum_folder).pack(side=LEFT, padx=5)
        self.check_lbl = tb.Label(sf, text="(none)")
        self.check_lbl.pack(side=LEFT, padx=5)

        cols = ("file","checksum")
        tv = tb.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            tv.heading(c, text=c.title())
        tv.pack(fill=BOTH, expand=YES, padx=12, pady=6)
        tv.bind("<<TreeviewSelect>>", lambda _e, v=tv: self._on_tree_select(v))
        tv.bind("<Double-1>", lambda _e: os.startfile(tv.item(tv.selection()[0])["values"][0]) if tv.selection() else None)
        self.check_tv = tv
        self._make_tree_sortable(tv)

        btn_box = tb.Frame(f); btn_box.pack(pady=4)
        tb.Button(btn_box, text="MD5",  bootstyle=PRIMARY, command=lambda: self._start_checksum("md5")).pack(side=LEFT, padx=6)
        tb.Button(btn_box, text="SHA1", bootstyle=PRIMARY, command=lambda: self._start_checksum("sha1")).pack(side=LEFT, padx=6)

    def _pick_checksum_files(self):
        fs = filedialog.askopenfilenames()
        if fs:
            self.check_files = list(fs)
            self.check_lbl.config(text=f"{len(fs)} files")

    def _pick_checksum_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        fl = []
        for r, _, files in os.walk(d):
            for f in files:
                fl.append(os.path.join(r, f))
        self.check_files = fl
        self.check_lbl.config(text=f"{len(fl)} files")

    def _start_checksum(self, mode):
        if not getattr(self, "check_files", None):
            return messagebox.showwarning("Checksum","Pick files or folder")
        TaskWindow("Checksums", self).start(self._checksum_worker, (mode,))

    def _checksum_worker(self, mode, status_cb):
        tv = self.check_tv
        self.after(0, lambda: tv.delete(*tv.get_children()))
        for f in self.check_files:
            h = hashlib.new(mode)
            try:
                with open(f, "rb") as fp:
                    for chunk in iter(lambda: fp.read(8192), b""):
                        h.update(chunk)
            except Exception:
                res = (f, "ERROR")
            else:
                res = (f, h.hexdigest())
            self.after(0, lambda r=res: tv.insert("", "end", values=r))
        status_cb("Done")

    # ------------------ ROBOCOPY Danger Tab ------------------
    def _build_robocopy_danger(self, nb):
        tab = tb.Frame(nb)
        nb.add(tab, text="Robocopy – Danger Zone")

        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "⚠️ Robocopy /MIR will mirror source to destination\n"
                "1) Select Source and Destination drives\n"
                "2) Type confirmation phrase\n"
                "3) Click Start"
            ),
            justify=LEFT, anchor="w"
        ).pack(fill=X, padx=15, pady=5)

        tb.Label(
            tab,
            text=textwrap.dedent(
                """
                ⚠️ Robocopy can and WILL obliterate data if you pick the wrong target.
                The /MIR flag mirrors source to destination – missing files in the
                source get deleted from the destination. Triple-check drive letters.
                """
            ).strip(),
            wraplength=780, justify=LEFT, foreground="#C00000"
        ).pack(fill=X, padx=12, pady=(0,8))

        frm = tb.Frame(tab); frm.pack(fill=X, padx=12, pady=6)
        tb.Label(frm, text="Source Drive:").pack(side=LEFT)
        self.robocopy_src = tb.Combobox(frm, values=self._list_drive_letters(), width=10)
        self.robocopy_src.pack(side=LEFT, padx=5)
        tb.Label(frm, text="Destination Drive:").pack(side=LEFT, padx=(10,0))
        self.robocopy_dst = tb.Combobox(frm, values=self._list_drive_letters(), width=10)
        self.robocopy_dst.pack(side=LEFT, padx=5)

        phrase_box = tb.Frame(tab); phrase_box.pack(fill=X, padx=12, pady=(4,2))
        tb.Label(phrase_box, text='Type "I UNDERSTAND DATA LOSS" to confirm:').pack(side=LEFT)
        self.phrase_var = tk.StringVar()
        tb.Entry(phrase_box, textvariable=self.phrase_var, width=24).pack(side=LEFT, padx=6)

        tb.Button(tab, text="Start Robocopy", bootstyle=DANGER, command=self._verify_robocopy).pack(pady=10)

    def _list_drive_letters(self):
        return [p.device.rstrip("\\") for p in psutil.disk_partitions(all=False)]

    def _verify_robocopy(self):
        src, dst = self.robocopy_src.get(), self.robocopy_dst.get()
        if not src or not dst:
            return messagebox.showwarning("Robocopy","Pick both drives")
        if src == dst:
            return messagebox.showwarning("Robocopy","Source and destination must differ")
        if self.phrase_var.get().strip().upper() != "I UNDERSTAND DATA LOSS":
            return messagebox.showwarning("Robocopy","Type the exact phrase")
        steps = [
            f"Copy {src} → {dst}?",
            "Warning: final confirmation",
        ]
        for msg in steps:
            if not messagebox.askyesno("Confirm", msg):
                messagebox.showinfo("Cancelled","Robocopy aborted.")
                return
        TaskWindow(f"Copy {src} → {dst}", self).start(self._drive_copy_worker, (src, dst))

    def _drive_copy_worker(self, src, dst, status_cb):
        status_cb("Starting robocopy …")
        cmd = ["robocopy", f"{src}\\", f"{dst}\\", "/MIR", "/R:1", "/W:1"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for ln in proc.stdout.splitlines():
            status_cb(ln.strip())
        status_cb("Done – review log for errors.")
