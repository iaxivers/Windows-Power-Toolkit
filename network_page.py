# pages/network_page.py
"""
Comprehensive network utilities GUI:
  • Network Info  – Interface details
  • My Host       – Local hostname/IP
  • Ping          – ICMP echo requests
  • Port Scan     – TCP port range scan
  • Subnet Scan   – Live host scanning in subnet
  • Reverse DNS   – PTR record lookup
  • Public IP     – External IP fetch
  • Domain → IP   – DNS resolution
  • Flood Test    – Stress test via UDP/TCP
  • Traceroute    – Hop-by-hop path

Each tab includes a step-by-step mini tutorial, labeled inputs,
determinate progress where appropriate, countdowns, and input validation.
"""
import subprocess
import socket
import ipaddress
import time
import threading
import tkinter as tk
import requests
import psutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox

# --- Helpers ---
def ping(host, count=4, timeout_ms=1000):
    try:
        return subprocess.check_output(
            f"ping -n {count} -w {timeout_ms} {host}", shell=True, text=True
        )
    except Exception as e:
        return f"Ping error: {e}"

def port_scan(host, start, end, timeout=0.2):
    open_ports = []
    for port in range(start, end+1):
        with socket.socket() as s:
            s.settimeout(timeout)
            if s.connect_ex((host, port)) == 0:
                open_ports.append(str(port))
    return "\n".join(open_ports) or "No open ports."

def reverse_dns(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception as e:
        return f"Reverse DNS error: {e}"

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=4).text
    except:
        return "Error retrieving public IP."

def domain_to_ip(domain):
    domain = domain.replace("http://","")
    domain = domain.replace("https://","")
    domain = domain.rstrip("/")
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        return f"Domain lookup error: {e}"

def flood_test(host, port, protocol, size, duration, progress_callback=None):
    end = time.time() + duration
    count = 0
    try:
        while time.time() < end:
            if protocol == "TCP":
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((host, port))
                    s.send(b"A" * size)
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.sendto(b"A" * size, (host, port))
            count += 1
            if progress_callback:
                progress_callback(count)
        return f"Sent {count} packets to {host}:{port} via {protocol}"
    except Exception as e:
        return f"Flood error: {e}"

def get_host_info():
    name = socket.gethostname()
    try:
        ip = socket.gethostbyname(name)
    except:
        ip = "Unavailable"
    return f"Hostname: {name}\nLocal IP: {ip}"

def traceroute(host):
    try:
        return subprocess.check_output(
            f"tracert {host}", shell=True, text=True
        )
    except Exception as e:
        return f"Traceroute error: {e}"


# --- GUI ---
class NetworkPage(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        pad = dict(padx=10, pady=8)
        tb.Label(self, text="Network Utilities", font=(None, 16, 'bold')).pack(anchor='w', **pad)
        nb = tb.Notebook(self)
        nb.pack(fill=BOTH, expand=YES, padx=12, pady=8)

        # Network Info tab styled like SystemInfoPage
        net_tab = tb.Frame(nb)
        nb.add(net_tab, text="Network")
        # tutorial for network tab
        tut = tb.Labelframe(net_tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(
            tut,
            text=(
                "1) Addresses: lists each IPv4 address and netmask\n"
                "2) Stats (speed/MTU): shows link speed in Mb and MTU size\n"
                "3) I/O: cumulative KB sent and received since boot\n"
                "4) Updates automatically every second"
            ),
            justify=LEFT,
            anchor='w'
        ).pack(fill=X, padx=15, pady=5)
        # build interface rows and keep references
        self.network_rows = {}
        for iface in psutil.net_if_addrs():
            grp = tb.Labelframe(net_tab, text=iface, bootstyle="secondary")
            grp.pack(fill=X, padx=10, pady=5)
            addr_lbl = self._add_row(grp, "Addresses")
            stat_lbl = self._add_row(grp, "Stats (speed/mtu)")
            io_lbl = self._add_row(grp, "I/O (KB sent/recv)")
            self.network_rows[iface] = (addr_lbl, stat_lbl, io_lbl)
        self.after(1000, self._update_network)

        # Tool tabs
        tabs = [
            ("My Host", self._host_tab, get_host_info, 1),
            ("Ping", self._ping_tab, ping, 3),
            ("Port Scan", self._port_tab, port_scan, 5),
            ("Subnet Scan", self._subnet_tab, None, 60),
            ("Reverse DNS", self._rev_tab, reverse_dns, 1),
            ("Public IP", self._pub_tab, get_public_ip, 1),
            ("Domain→IP", self._dom_tab, domain_to_ip, 1),
            ("Flood Test", self._flood_tab, flood_test, 5),
            ("Traceroute", self._tracert_tab, traceroute, 10),
        ]
        for title, builder, func, est in tabs:
            frm = tb.Frame(nb)
            nb.add(frm, text=title)
            builder(frm, func, est)

    def _add_row(self, parent, title):
        row = tb.Frame(parent)
        row.pack(fill=X, pady=2, padx=5)
        tb.Label(row, text=title, width=20, anchor='w').pack(side=LEFT)
        lbl = tb.Label(row, text='', anchor='w')
        lbl.pack(side=LEFT, fill=X, expand=YES)
        return lbl

    def _update_network(self):
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        io = psutil.net_io_counters(pernic=True)
        for iface, (addr_lbl, stat_lbl, io_lbl) in self.network_rows.items():
            ips = [f"{a.address}/{a.netmask}" for a in addrs.get(iface, []) if a.family==socket.AF_INET]
            addr_lbl.config(text=', '.join(ips) or 'N/A')
            st = stats.get(iface)
            stat_lbl.config(text=f"{st.speed}Mb/{st.mtu}" if st else 'N/A')
            cnt = io.get(iface)
            io_lbl.config(text=f"{cnt.bytes_sent//1024}/{cnt.bytes_recv//1024}" if cnt else '0/0')
        self.after(1000, self._update_network)

    def _with_loader(self, action, widget, est):
        dlg = tk.Toplevel(self)
        dlg.title("Working...")
        pb = tb.Progressbar(dlg, mode="indeterminate")
        pb.pack(fill=X, padx=20, pady=(20,4)); pb.start()
        lbl = tb.Label(dlg, text=f"Time left: {est}s")
        lbl.pack(padx=20, pady=(0,20))
        def tick(t):
            if t<0: return
            lbl.config(text=f"Time left: {t}s")
            dlg.after(1000, lambda: tick(t-1))
        tick(est)
        def run():
            res = action()
            dlg.destroy()
            widget.config(state="normal"); widget.delete("1.0","end"); widget.insert("1.0", res); widget.config(state="disabled")
        threading.Thread(target=run, daemon=True).start()

    def _host_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Click 'Get Host Info'\n2) Result below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        tb.Button(tab, text="Get Host Info", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(func, self.out_host, est)
                 ).pack(anchor=W, padx=10, pady=5)
        self.out_host = tb.Text(tab, height=2, state='disabled'); self.out_host.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _ping_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter host\n2) Click 'Ping'\n3) See results below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="Host:").pack(side=LEFT)
        ent = tb.Entry(frm, width=30); ent.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Ping", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(lambda: func(ent.get()), self.out_ping, est)
                 ).pack(side=LEFT, padx=5)
        self.out_ping = tb.Text(tab, height=10, state='disabled'); self.out_ping.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _port_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter host and port range (e.g. 20-80)\n2) Click 'Scan'\n3) Open ports listed below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="Host:").pack(side=LEFT)
        he = tb.Entry(frm, width=18); he.pack(side=LEFT, padx=(5,10))
        tb.Label(frm, text="Ports:").pack(side=LEFT)
        pe = tb.Entry(frm, width=12); pe.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Scan", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(
                      lambda: func(he.get(), *(map(int, pe.get().split('-')))),
                      self.out_port, est)
                 ).pack(side=LEFT, padx=5)
        self.out_port = tb.Text(tab, height=10, state='disabled'); self.out_port.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _subnet_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter CIDR (e.g. 192.168.1.0/24)\n2) Click 'Scan'\n3) Live hosts listed below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="CIDR:").pack(side=LEFT)
        ce = tb.Entry(frm, width=24); ce.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Scan", bootstyle=PRIMARY,
                  command=lambda: threading.Thread(target=self._scan_subnet, args=(ce.get(), est), daemon=True).start()
                 ).pack(side=LEFT, padx=5)
        self.out_sub = tb.Text(tab, height=10, state='disabled'); self.out_sub.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _scan_subnet(self, cidr, est):
        self.out_sub.config(state='normal'); self.out_sub.delete('1.0','end')
        try:
            hosts = list(ipaddress.ip_network(cidr, strict=False).hosts())
        except:
            messagebox.showerror("Invalid CIDR","Enter a valid subnet."); return
        for ip in hosts:
            if subprocess.call(f"ping -n 1 -w 200 {ip}", shell=True) == 0:
                self.out_sub.insert('end', f"{ip}\n"); self.out_sub.see('end')
        self.out_sub.config(state='disabled')

    def _rev_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter IP\n2) Click 'Lookup'\n3) Hostname below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="IP:").pack(side=LEFT)
        ie = tb.Entry(frm, width=24); ie.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Lookup", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(lambda: func(ie.get()), self.out_rev, est)
                 ).pack(side=LEFT, padx=5)
        self.out_rev = tb.Text(tab, height=6, state='disabled'); self.out_rev.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _pub_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Click 'Fetch Public IP'\n2) IP below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        tb.Button(tab, text="Fetch Public IP", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(func, self.out_pub, est)
                 ).pack(anchor=W, padx=10, pady=5)
        self.out_pub = tb.Text(tab, height=2, state='disabled'); self.out_pub.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _dom_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter domain or URL\n2) Click 'Resolve'\n3) IP below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="Domain:").pack(side=LEFT)
        de = tb.Entry(frm, width=30); de.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Resolve", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(lambda: func(de.get()), self.out_dom, est)
                 ).pack(side=LEFT, padx=5)
        self.out_dom = tb.Text(tab, height=6, state='disabled'); self.out_dom.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _flood_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Fill Host, Port, Proto, Size, Dur\n2) Click 'Start Flood'\n3) Result below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        entries = {}
        for label,width in [("Host",18),("Port",6),("Proto",6),("Size",6),("Dur",6)]:
            tb.Label(frm, text=f"{label}:").pack(side=LEFT)
            e = tb.Entry(frm, width=width); e.pack(side=LEFT, padx=(5,0))
            entries[label] = e
        tb.Button(frm, text="Start Flood", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(
                      lambda: func(
                          entries["Host"].get(),
                          int(entries["Port"].get()),
                          entries["Proto"].get().upper(),
                          int(entries["Size"].get()),
                          int(entries["Dur"].get()),
                          None
                      ),
                      self.out_flood,
                      est
                  )
                 ).pack(side=LEFT, padx=5)
        self.out_flood = tb.Text(tab, height=4, state='disabled'); self.out_flood.pack(fill=BOTH, expand=YES, padx=10, pady=5)

    def _tracert_tab(self, tab, func, est):
        tut = tb.Labelframe(tab, text="How to Use", bootstyle=INFO)
        tut.pack(fill=X, padx=10, pady=5)
        tk.Label(tut, text="1) Enter host or IP\n2) Click 'Trace'\n3) Hops below", justify=LEFT, anchor='w').pack(fill=X, padx=15)
        frm = tb.Frame(tab); frm.pack(anchor=W, padx=10, pady=5)
        tb.Label(frm, text="Host:").pack(side=LEFT)
        tr_e = tb.Entry(frm, width=30); tr_e.pack(side=LEFT, padx=(5,0))
        tb.Button(frm, text="Trace", bootstyle=PRIMARY,
                  command=lambda: self._with_loader(lambda: func(tr_e.get()), self.out_tr, est)
                 ).pack(side=LEFT, padx=5)
        self.out_tr = tb.Text(tab, height=10, state='disabled'); self.out_tr.pack(fill=BOTH, expand=YES, padx=10, pady=5)
