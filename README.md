# MCSmaker

MCSmaker is a simple Python-based tool to manage Minecraft servers with ease. It provides an interactive menu-driven interface to download server JARs, set up servers, and control them using `screen` sessions.

---

## ✨ Features

- **Interactive menu-based interface**
- **Download Minecraft server JARs directly from Mojang**
- **Create full server setups**:
  - Generates `eula.txt`, `server.properties`, and `start.sh`
  - Default memory allocation: 4GB
- **Manage multiple servers**:
  - Start, stop, view console, and backup servers
  - View logs directly from the manager
  - List all servers
  - Delete servers
- **Configurable settings**:
  - Java path
  - Default RAM size
  - JARs and server directories
- **System integration**:
  - Works on Linux & WSL
  - Uses `screen` for server sessions
  - Installer (`install.sh`) auto-updates itself and downloads the latest manager
  - Creates a global `mcsmaker` command for easy use

---

## 📦 Installation

Clone the repo and run the installer:

```bash
git clone https://github.com/Nico19422009/MCSmaker.git
cd MCSmaker
./install.sh
```

This will:
- Install Python, Java, and Screen
- Download the latest `manager.py`
- Create a global `mcsmaker` command

---

## 🚀 Usage

Start the manager with:

```bash
mcsmaker
```

Follow the interactive menu to:
- Download JARs
- Create servers
- Start/Stop servers
- Backup servers
- View logs
- Change settings

Attach to a running server console:
```bash
screen -r mc_<servername>
```
(Detach with `CTRL+A+D`)

---

## 📖 Patch Notes v1.5.0

- Servers now run inside dedicated `screen` sessions
- Added server backup, log view, and console hints
- Improved start/stop handling
- Installer now auto-updates itself and creates global `mcsmaker` shortcut
- Cleaner error handling and bug fixes

---

## 🔗 Links

- [GitHub Repo](https://github.com/Nico19422009/MCSmaker)
