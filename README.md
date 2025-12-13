# MCSmaker

MCSmaker is a simple Python-based tool to manage Minecraft servers with ease. It provides an interactive menu-driven interface to download server JARs, set up servers, and control them using `screen` sessions.

---

## ✨ Features

- **Interactive menu-based interface**
- **Download Minecraft server JARs**
  - Vanilla directly from Mojang
  - Paper, Fabric, and Forge installers/builds
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
- Install Python, Java 17 (falls back to distro default), and Screen
- Download the latest `manager.py`
- Create a global `mcsmaker` command

---

## 🚀 Usage

Start the manager with:

```bash
mcsmaker
```

Follow the interactive menu to:
- Download JARs (vanilla, Paper, Fabric, Forge)
- Create servers (vanilla, Paper, Fabric, Forge)
- Start/Stop servers
- Backup servers
- View logs
- Change settings

> **Java version:** Minecraft servers need Java 8+, and modern versions expect Java 17+. The installer tries to pull OpenJDK 17 and the manager will warn if it detects an older runtime. You can point to a custom Java binary under **Settings → Java** if needed.

Attach to a running server console:
```bash
screen -r mc_<servername>
```
(Detach with `CTRL+A+D`)

---

## 📖 Patch Notes

### v1.7.0
- Added Java runtime checks with warnings when the detected version is below Java 8 and guidance to use Java 17+
- Installer now prefers installing OpenJDK 17, falling back to the distro default JDK if needed
- Clarified Java expectations and installer behavior in the usage documentation

### v1.6.1
- Added Paper downloads to the JAR manager alongside Fabric and Forge
- Updated modded server creation flow to include Paper as a selectable loader
- Improved vanilla download handling to avoid duplicate partial files in the cache

---

## 🔗 Links

- [GitHub Repo](https://github.com/Nico19422009/MCSmaker)
