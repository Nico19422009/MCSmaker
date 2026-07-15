# MCSmaker

MCSmaker is a Minecraft server manager. It has an Electron GUI for desktops and a Linux-first CLI for headless servers.

## Features

- Create, download, start and stop real Java servers
- Vanilla, Paper, Fabric and Forge support
- JAR downloads use mcutils, e.g. `https://mcutils.com/api/server-jars/paper/26.2/download`
- One folder, `server.jar`, EULA file and persistent configuration per server
- Detached Linux starts with PID tracking and logs in `logs/mcsmaker.log`
- RAM limit per server, such as `2G`

## Linux server / CLI

Requires Node.js 18+ and Java for the Minecraft version you choose.

```bash
git clone https://github.com/Nico19422009/MCSmaker.git
cd MCSmaker
chmod +x bin/mcsmaker bin/mcsmaker-cli.js

# Create + download a Paper server
./bin/mcsmaker create survival 1.21.8 paper 4G

# Find the server ID, then start or stop it
./bin/mcsmaker list
./bin/mcsmaker start <server-id>
./bin/mcsmaker stop <server-id>
```

Server files and the manager database are stored in `~/.local/share/mcsmaker` by default. Set `MCSMAKER_HOME` to use another folder.

## Desktop GUI

```bash
npm install
npm start
```

The GUI lets you choose the loader, Minecraft version and memory before it downloads the server.

## Notes

Forge and Fabric are downloaded through mcutils as requested. The selected version has to be available from the mcutils server-jars endpoint.
