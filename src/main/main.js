const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const manager = require('../core/server-manager');

const APP_TITLE = 'MCSmaker';

function createWindow() {
  const win = new BrowserWindow({
    width: 1200, height: 760, minWidth: 1000, minHeight: 600, title: APP_TITLE,
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false }
  });
  win.loadFile(path.join(__dirname, '../renderer/index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (!BrowserWindow.getAllWindows().length) createWindow(); });
});
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });

const response = (fn) => async (...args) => {
  try { return await fn(...args); }
  catch (error) { return { error: error.message }; }
};
ipcMain.handle('servers:list', response(() => manager.listServers()));
ipcMain.handle('servers:create', response(async (_event, payload) => {
  const server = await manager.createServer(payload || {});
  return { server, servers: manager.listServers() };
}));
ipcMain.handle('servers:start', response((_event, id) => ({ server: manager.startServer(id), servers: manager.listServers() })));
ipcMain.handle('servers:stop', response((_event, id) => ({ server: manager.stopServer(id), servers: manager.listServers() })));
ipcMain.handle('versions:list', () => ({ versions: ['1.21.8', '1.21.7', '1.21.6', '1.20.6', '1.20.4', '1.19.4'] }));
ipcMain.handle('loaders:list', () => ({ loaders: [...manager.SUPPORTED_LOADERS] }));