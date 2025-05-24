import ttkbootstrap as tb
from ttkbootstrap.constants import *

class HelpPage(tb.Frame):
    def __init__(self, master):
        super().__init__(master)
        pad = dict(padx=12, pady=12)

        tv = tb.Text(self, wrap="word")
        tv.insert("1.0",
            "Windows Power Toolkit\n\n"
            "Home\n"
            "• Shows an introduction and the current version of this app.\n\n"
            "Help\n"
            "• Help section, this is the page you're currently in.\n\n"
            "Storage\n"
            "• Overview: lists your drives with total, used, and free space, filesystem type, and cluster size.\n"
            "• Drive Usage Chart: visual pie chart of used vs free space.\n"
            "• Speed Test: measures write and read speed by writing/reading a temp file.\n"
            "• Unmount/Eject/ISO: unmounts volumes, ejects media, and mounts or dismounts ISO files.\n"
            "• Format: safely formats a drive as NTFS, FAT32, or exFAT (all data lost).\n"
            "• Cleanup: temp files, recycle bin, browser cache, and Windows cache, each in its own tab.\n"
            "• File Manager: search folders, find duplicates, remove empty folders, compute checksums.\n"
            "• Robocopy – Danger Zone: mirrors one drive to another (use with extreme care).\n\n"
            "Network\n"
            "• Network Info: shows each interface’s IP addresses, link speed, MTU, and cumulative I/O.\n"
            "• My Host: local hostname and IP address lookup.\n"
            "• Ping: ICMP echo requests to test reachability and latency.\n"
            "• Port Scan: checks a range of TCP ports for openness.\n"
            "• Subnet Scan: live sweep of hosts in a CIDR subnet.\n"
            "• Reverse DNS: PTR lookup to find hostnames for IP addresses.\n"
            "• Public IP: fetches your external IP from an online service.\n"
            "• Domain → IP: resolves a domain name or URL to its IP address.\n"
            "• Flood Test: sends a burst of UDP or TCP packets to test throughput.\n"
            "• Traceroute: shows the hop-by-hop path to a remote host.\n\n"
            "System Info\n"
            "• Operating System: version, build number, and architecture.\n"
            "• CPU: make, model, core count, and current utilization.\n"
            "• RAM: total, used, free, and usage percentage.\n"
            "• Disks: detailed partition and volume information.\n"
            "• GPU: graphics adapter details and memory usage.\n"
            "• Uptime: how long the system has been running.\n\n"
            "Use the sidebar to switch between pages."
        )
        tv.configure(state="disabled")
        tv.pack(fill=BOTH, expand=YES, **pad)
