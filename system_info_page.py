import platform
import psutil
import socket
import uuid
import datetime
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class SystemInfoPage(tb.Frame):
    """
    Live system info updating every second.
    Tabs: General, CPU, Memory, Disk, Network, Users.
    """
    def __init__(self, master):
        super().__init__(master)
        pad = dict(padx=10, pady=5)

        # Header
        tb.Label(self, text="System Information", font=(None, 16, 'bold')).pack(anchor='w', **pad)

        # Tabs
        notebook = tb.Notebook(self)
        notebook.pack(fill=BOTH, expand=YES, **pad)
        self.tabs = {name: tb.Frame(notebook) for name in ["General","CPU","Memory","Disk","Network","Users"]}
        for name, frame in self.tabs.items():
            notebook.add(frame, text=name)

        # Build tab content
        self._build_general(self.tabs["General"])
        self._build_cpu(self.tabs["CPU"])
        self._build_memory(self.tabs["Memory"])
        self._build_disk(self.tabs["Disk"])
        self._build_network(self.tabs["Network"])
        self._build_users(self.tabs["Users"])

        # Start live update
        self._update_all()

    def _add_row(self, parent, title, colspan=1):
        frame = tb.Frame(parent)
        frame.pack(fill=X, pady=2, padx=5)
        tb.Label(frame, text=title, width=25, anchor='w').pack(side=LEFT)
        val = tb.Label(frame, text='')
        val.pack(side=LEFT)
        return val

    def _build_general(self, parent):
        self.node_lbl   = self._add_row(parent, "Node Name")
        self.system_lbl = self._add_row(parent, "System")
        self.release_lbl= self._add_row(parent, "Release")
        self.version_lbl= self._add_row(parent, "Version")
        self.machine_lbl= self._add_row(parent, "Machine")
        self.processor_lbl = self._add_row(parent, "Processor")
        self.arch_lbl   = self._add_row(parent, "Architecture")
        self.python_lbl = self._add_row(parent, "Python Version")
        self.mac_lbl    = self._add_row(parent, "MAC Address")
        self.uuid_lbl   = self._add_row(parent, "UUID")
        self.boot_lbl   = self._add_row(parent, "Boot Time")
        self.uptime_lbl = self._add_row(parent, "Uptime")

    def _build_cpu(self, parent):
        self.cpu_phy_lbl = self._add_row(parent, "CPU Cores (phy/log)")
        self.freq_lbl    = self._add_row(parent, "Freq (min/max/curr) MHz")
        self.usage_lbl   = self._add_row(parent, "Usage (%)")
        self.cpu_times_lbl = self._add_row(parent, "Times (usr/sys/idl)")
        self.ctx_lbl     = self._add_row(parent, "Context Switches")

    def _build_memory(self, parent):
        self.ram_lbl    = self._add_row(parent, "RAM Total/Used (%)")
        self.swap_lbl   = self._add_row(parent, "Swap Total/Used (%)")

    def _build_disk(self, parent):
        self.disk_parts_lbl = self._add_row(parent, "Partitions (mount)")
        self.disk_usage_lbl = self._add_row(parent, "Total/Used/Free (GB)")

    def _build_network(self, parent):
        # List each iface in separate labeled frame
        self.net_frames = {}
        for iface in psutil.net_if_addrs():
            grp = tb.Labelframe(parent, text=iface)
            grp.pack(fill=X, pady=4, padx=5)
            addr_lbl = self._add_row(grp, "Addresses")
            stats_lbl= self._add_row(grp, "Stats (speed/mtu)")
            io_lbl   = self._add_row(grp, "I/O (KB sent/recv)")
            self.net_frames[iface] = (addr_lbl, stats_lbl, io_lbl)

    def _build_users(self, parent):
        self.users_lbl = self._add_row(parent, "Logged In Users")

    def _get_mac(self):
        mac = uuid.getnode()
        return ':'.join(f"{(mac>>ele)&0xff:02x}" for ele in range(40,-8,-8))

    def _update_all(self):
        now = datetime.datetime.now()
        # General
        uname = platform.uname()
        self.node_lbl.config(text=uname.node)
        self.system_lbl.config(text=uname.system)
        self.release_lbl.config(text=uname.release)
        self.version_lbl.config(text=uname.version)
        self.machine_lbl.config(text=uname.machine)
        self.processor_lbl.config(text=uname.processor)
        self.arch_lbl.config(text=' '.join(platform.architecture()))
        self.python_lbl.config(text=platform.python_version())
        self.mac_lbl.config(text=self._get_mac())
        self.uuid_lbl.config(text=str(uuid.UUID(int=uuid.getnode())))
        bt = datetime.datetime.fromtimestamp(psutil.boot_time())
        self.boot_lbl.config(text=bt.strftime('%Y-%m-%d %H:%M:%S'))
        up = now - bt
        self.uptime_lbl.config(text=str(up).split('.')[0])
        # CPU
        phy = psutil.cpu_count(False); log = psutil.cpu_count(True)
        self.cpu_phy_lbl.config(text=f"{phy}/{log}")
        freq = psutil.cpu_freq()
        if freq: fmt = f"{freq.min:.0f}/{freq.max:.0f}/{freq.current:.0f}"
        else: fmt = "N/A"
        self.freq_lbl.config(text=fmt)
        self.usage_lbl.config(text=f"{psutil.cpu_percent(None)}")
        ct = psutil.cpu_times()
        self.cpu_times_lbl.config(text=f"{ct.user:.1f}/{ct.system:.1f}/{ct.idle:.1f}")
        self.ctx_lbl.config(text=f"{psutil.cpu_stats().ctx_switches}")
        # Memory
        vm = psutil.virtual_memory()
        self.ram_lbl.config(text=f"{vm.total//(1024**3)}GB/{vm.percent}")
        sm = psutil.swap_memory()
        self.swap_lbl.config(text=f"{sm.total//(1024**3)}GB/{sm.percent}")
        # Disk
        parts = psutil.disk_partitions()
        mounts = ', '.join(p.mountpoint for p in parts)
        self.disk_parts_lbl.config(text=mounts)
        du = psutil.disk_usage('/')
        self.disk_usage_lbl.config(text=f"{du.total//(1024**3)}/{du.used//(1024**3)}/{du.free//(1024**3)}")
        # Network
        stats = psutil.net_if_stats(); addrs = psutil.net_if_addrs(); io = psutil.net_io_counters()
        for iface, (addr_lbl, stats_lbl, io_lbl) in self.net_frames.items():
            # addresses
            ips = [f"{a.address}/{a.netmask}" for a in addrs.get(iface,[]) if a.family==socket.AF_INET]
            addr_lbl.config(text=', '.join(ips) or 'N/A')
            # stats
            st = stats.get(iface)
            if st: stats_lbl.config(text=f"{st.speed}Mb/ {st.mtu}")
            # I/O totals
            io_lbl.config(text=f"{io.bytes_sent//1024}/{io.bytes_recv//1024}")
        # Users
        users = psutil.users()
        self.users_lbl.config(text=', '.join(u.name for u in users) or 'None')
        # Refresh every second
        self.after(1000, self._update_all)
