const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('mcsmaker', {
  listServers: () => ipcRenderer.invoke('servers:list'),
  createServer: (payload) => ipcRenderer.invoke('servers:create', payload),
  startServer: (serverId) => ipcRenderer.invoke('servers:start', serverId),
  stopServer: (serverId) => ipcRenderer.invoke('servers:stop', serverId),
  listVersions: () => ipcRenderer.invoke('versions:list'),
  listLoaders: () => ipcRenderer.invoke('loaders:list')
});
