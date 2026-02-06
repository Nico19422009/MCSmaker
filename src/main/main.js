const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');

const APP_TITLE = 'MCSmaker Launcher';

const ensureDir = (dirPath) => {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
};

const getUserDataPath = () => app.getPath('userData');
const getServersRoot = () => path.join(getUserDataPath(), 'servers');
const getServerStorePath = () => path.join(getUserDataPath(), 'mcsmaker-servers.json');
const getVersionsPath = () => path.join(app.getAppPath(), 'servers.json');

const readJsonFile = (filePath, fallback) => {
  if (!fs.existsSync(filePath)) {
    return fallback;
  }
  const raw = fs.readFileSync(filePath, 'utf-8');
  try {
    return JSON.parse(raw);
  } catch (error) {
    return fallback;
  }
};

const writeJsonFile = (filePath, data) => {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf-8');
};

const sanitizeName = (value) => value.trim().replace(/[^a-zA-Z0-9_-]/g, '_');

const readServerStore = () => readJsonFile(getServerStorePath(), { servers: [] });

const listVersions = () => {
  const versionsData = readJsonFile(getVersionsPath(), { servers: [] });
  const seen = new Set();
  const result = [];
  for (const entry of versionsData.servers || []) {
    const name = entry.name;
    if (!name || seen.has(name)) {
      continue;
    }
    seen.add(name);
    result.push(name);
  }
  return result;
};

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 760,
    minWidth: 1000,
    minHeight: 600,
    title: APP_TITLE,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  win.loadFile(path.join(__dirname, '../renderer/index.html'));
};

app.whenReady().then(() => {
  ensureDir(getServersRoot());
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('servers:list', () => {
  const store = readServerStore();
  return store.servers;
});

ipcMain.handle('servers:create', (event, payload) => {
  const store = readServerStore();
  const name = sanitizeName(payload?.name || '');
  const version = payload?.version || '';

  if (!name || !version) {
    return { error: 'Name and version are required.' };
  }

  const exists = store.servers.some((server) => server.name.toLowerCase() === name.toLowerCase());
  if (exists) {
    return { error: 'A server with this name already exists.' };
  }

  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const serverDir = path.join(getServersRoot(), name);
  ensureDir(serverDir);

  const newServer = {
    id,
    name,
    version,
    status: 'stopped',
    createdAt: new Date().toISOString(),
    path: serverDir,
    lastStartedAt: null
  };

  store.servers.push(newServer);
  writeJsonFile(getServerStorePath(), store);

  return { server: newServer, servers: store.servers };
});

ipcMain.handle('servers:start', (event, serverId) => {
  const store = readServerStore();
  const server = store.servers.find((entry) => entry.id === serverId);
  if (!server) {
    return { error: 'Server not found.' };
  }

  store.servers = store.servers.map((entry) => {
    if (entry.id === serverId) {
      return {
        ...entry,
        status: 'running',
        lastStartedAt: new Date().toISOString()
      };
    }
    return entry;
  });

  writeJsonFile(getServerStorePath(), store);
  return { servers: store.servers };
});

ipcMain.handle('servers:stop', (event, serverId) => {
  const store = readServerStore();
  const server = store.servers.find((entry) => entry.id === serverId);
  if (!server) {
    return { error: 'Server not found.' };
  }

  store.servers = store.servers.map((entry) => {
    if (entry.id === serverId) {
      return {
        ...entry,
        status: 'stopped'
      };
    }
    return entry;
  });

  writeJsonFile(getServerStorePath(), store);
  return { servers: store.servers };
});

ipcMain.handle('versions:list', () => ({ versions: listVersions() }));
