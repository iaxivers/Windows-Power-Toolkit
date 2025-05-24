# Windows Power Toolkit

A single GUI for core Windows tools. Run diagnostics, network tests, storage scans, and system info in one place. Built for power users, sysadmins, and engineers.

**DISCLAIMER: I AM UNSURE IF THE TOOL WILL GET UPDATED! I DON'T HAVE ANY SPECIFIC IDEAS FOR IT! WORKS FINE FOR NOW THOUGH!**

## Features

- **Home**  
  Intro screen with version and quick links.

- **Help**  
  Tutorial screen.

- **Storage**  
  - Overview of drives with total, used, free, filesystem, cluster size  
  - Pie chart of used vs free space  
  - Speed test (write/read)  
  - Unmount, eject, ISO mount/dismount  
  - Format drives (NTFS, FAT32, exFAT)  
  - Cleanup tabs: temp files, recycle bin, browser cache, Windows cache  
  - File Manager: search, duplicates, empty folders, checksums  
  - Robocopy “Danger Zone” for safe mirroring

- **Network**  
  - Interface info (IP, speed, MTU, I/O) auto-refresh every second  
  - Hostname & local IP lookup  
  - Ping utility  
  - TCP port scan  
  - Subnet sweep  
  - Reverse DNS lookup  
  - Public IP fetch  
  - Domain to IP resolution  
  - Flood test (UDP/TCP packet send)  
  - Traceroute

- **System Info**  
  OS version, CPU details, RAM usage, disk layout, GPU info, uptime.

- **Utilities**  
  Quick-launch buttons for PowerShell, Registry Editor, Command Prompt, Task Manager.

## Requirements

- Windows 10 or later  
- Python 3.8+  
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap)  
- `psutil`, `wmi`, `requests`, `matplotlib`  
- Optional: `send2trash`, `winshell` for recycle-bin support

**Installation**

1. Clone the repo:  
   
    ```bash
    git clone https://github.com/your-username/your-repo.git  
    cd your-repo  

2. Create and activate a virtual environment:  
   
    ```bash
     python -m venv .venv  
    .venv\Scripts\activate  

3. Install dependencies:  
   
    ```bash
   pip install -r requirements.txt  

4. Run the app:  
   
   ```bash
   python Main.py  

*Optional: Build a standalone EXE*

1. Install PyInstaller:  
   
    ```bash
    pip install pyinstaller  

2. Bundle into one file, windowed mode:  
   
    ```bash
    pyinstaller --onefile --windowed Main.py  

3. Find your `Main.exe` in the `dist` folder.  

## IF YOU ENCOUNTER ANY ISSUES FEEL FREE TO DM ME ON DISCORD @iaxivers
