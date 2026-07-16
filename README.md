# MCSMaker 1.6.0

MCSMaker is now one interactive terminal program made for Linux servers.

It shows an ASCII banner and lets you control everything through numbered menus. No Electron or desktop is required.

## Features

- Vanilla, Paper, Fabric and Forge through mcutils
- Create and download servers
- Start and stop real Java processes
- Server status and PID display
- RAM selection
- Last 40 log lines
- Full server backups
- Safe server deletion with confirmation
- Java, Node.js, storage and system check
- Persistent data in `~/.local/share/mcsmaker`

## Start

You need Node.js 18 or newer and the Java version required by your Minecraft server.

```bash
git clone https://github.com/Nico19422009/MCSmaker.git
cd MCSmaker
npm start
```

You can also start the single program directly:

```bash
node mcsmaker.js
```

The program then opens this menu:

```text
1) Neuen Server erstellen
2) Server starten
3) Server stoppen
4) Serverliste und Status
5) Logs anzeigen
6) Backup erstellen
7) Server löschen
8) Systemcheck
0) Beenden
```

## Optional global command

```bash
sudo npm install -g .
mcsmaker
```

Set `MCSMAKER_HOME` if you want another data directory:

```bash
MCSMAKER_HOME=/srv/minecraft npm start
```
