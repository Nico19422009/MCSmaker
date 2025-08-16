# MCSmaker

MCSmaker is a lightweight automation tool to **download, build, and manage Minecraft servers** with ease.  
It supports fetching official server JARs directly from Mojang, creating isolated server folders with custom `start.sh` launch scripts, and running servers inside `screen` sessions.

---

## ✨ Features
- Interactive **menu-based interface**
- Download **Minecraft server JARs** directly from Mojang
- Create full server setups:
  - Generates `eula.txt`, `server.properties`, and `start.sh`
  - Default memory allocation: **4GB**
- Manage multiple servers:
  - List all servers
  - Delete servers
  - Start servers in background `screen` sessions
- Configurable settings:
  - Java path
  - Default RAM size
  - JARs and server directories
- Works on Linux & WSL

---

## 📦 Installation

Clone the repository and run the installer:

```bash
git clone https://github.com/yourusername/MCSmaker.git
cd MCSmaker
chmod +x install.sh
./install.sh
