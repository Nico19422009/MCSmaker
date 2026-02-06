# MCSmaker Launcher

MCSmaker is now an Electron-based Minecraft server launcher. It gives you a clean GUI to list servers, start them with a play button, and create new server entries with a name and version selection.

---

## ✨ Features

- **Server list with play buttons** for quick launches
- **Server detail panel** with status and folder info
- **Create new servers** by choosing a Minecraft version and naming the server
- **Local data storage** in your system's user data directory

---

## 📦 Setup

Install dependencies and start the Electron app:

```bash
npm install
npm start
```

---

## 🗂️ Data

- Server entries are saved in your Electron user data path as `mcsmaker-servers.json`.
- Created server folders live under `servers/` inside the same user data path.
- Version options are loaded from `servers.json` in this repo.

---

## 📝 Notes

The original Python CLI remains in the repository for reference, but the Electron GUI is now the primary interface for launching and managing servers.
