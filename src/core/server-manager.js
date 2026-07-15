const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const crypto = require('crypto');

const SUPPORTED_LOADERS = new Set(['vanilla', 'paper', 'fabric', 'forge']);
const dataDir = () => process.env.MCSMAKER_HOME || path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'), 'mcsmaker');
const serversRoot = () => path.join(dataDir(), 'servers');
const storePath = () => path.join(dataDir(), 'servers.json');

function ensure(dir) { fs.mkdirSync(dir, { recursive: true }); }
function readStore() {
  try { return JSON.parse(fs.readFileSync(storePath(), 'utf8')); }
  catch { return { servers: [] }; }
}
function writeStore(store) {
  ensure(dataDir());
  fs.writeFileSync(storePath(), JSON.stringify(store, null, 2) + '\n');
}
function safeName(value) {
  const name = String(value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_');
  if (!name || name === '.' || name === '..') throw new Error('Use a valid server name.');
  return name;
}
function jarUrl(loader, version) {
  if (!SUPPORTED_LOADERS.has(loader)) throw new Error('Unsupported loader: ' + loader);
  if (!/^[0-9A-Za-z._-]+$/.test(version)) throw new Error('Use a valid Minecraft version.');
  return 'https://mcutils.com/api/server-jars/' + loader + '/' + version + '/download';
}
async function download(url, destination) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok || !response.body) throw new Error('Download failed: HTTP ' + response.status);
  const file = fs.createWriteStream(destination);
  await new Promise((resolve, reject) => {
    response.body.pipeTo(new WritableStream({
      write(chunk) { return new Promise((ok, fail) => file.write(chunk, e => e ? fail(e) : ok())); },
      close() { file.end(resolve); },
      abort(error) { file.destroy(error); reject(error); }
    })).catch(reject);
  });
}
async function createServer({ name, version, loader = 'vanilla', memory = '2G' }) {
  name = safeName(name);
  loader = String(loader).toLowerCase();
  version = String(version || '').trim();
  if (!version) throw new Error('Minecraft version is required.');
  if (!/^\d+(?:\.\d+){1,2}(?:[-A-Za-z0-9._]+)?$/.test(version)) throw new Error('Use a valid Minecraft version.');
  if (!/^\d+[MG]$/i.test(memory)) throw new Error('Memory must look like 2G or 1024M.');
  const store = readStore();
  if (store.servers.some(s => s.name.toLowerCase() === name.toLowerCase())) throw new Error('A server with this name already exists.');
  const dir = path.join(serversRoot(), name);
  ensure(dir);
  const jar = path.join(dir, 'server.jar');
  try {
    await download(jarUrl(loader, version), jar);
  } catch (error) {
    fs.rmSync(dir, { recursive: true, force: true });
    throw error;
  }
  fs.writeFileSync(path.join(dir, 'eula.txt'), 'eula=true\n');
  const server = { id: crypto.randomUUID(), name, version, loader, memory: memory.toUpperCase(), path: dir, jar, status: 'stopped', createdAt: new Date().toISOString(), lastStartedAt: null, pid: null };
  store.servers.push(server);
  writeStore(store);
  return server;
}
function listServers() { return readStore().servers.map(refreshStatus); }
function refreshStatus(server) {
  if (server.pid) {
    try { process.kill(server.pid, 0); return { ...server, status: 'running' }; }
    catch { return { ...server, status: 'stopped', pid: null }; }
  }
  return { ...server, status: 'stopped' };
}
function saveServer(updated) {
  const store = readStore();
  const index = store.servers.findIndex(s => s.id === updated.id);
  if (index === -1) throw new Error('Server not found.');
  store.servers[index] = updated;
  writeStore(store);
}
function getServer(id) {
  const server = readStore().servers.find(s => s.id === id);
  if (!server) throw new Error('Server not found.');
  return refreshStatus(server);
}
function startServer(id, detached = true) {
  const server = getServer(id);
  if (server.status === 'running') return server;
  if (!fs.existsSync(server.jar)) throw new Error('server.jar is missing.');
  ensure(path.join(server.path, 'logs'));
  const log = fs.openSync(path.join(server.path, 'logs', 'mcsmaker.log'), 'a');
  const child = spawn('java', ['-Xms' + server.memory, '-Xmx' + server.memory, '-jar', 'server.jar', 'nogui'], { cwd: server.path, detached, stdio: ['ignore', log, log] });
  child.unref();
  const updated = { ...server, status: 'running', pid: child.pid, lastStartedAt: new Date().toISOString() };
  saveServer(updated);
  return updated;
}
function stopServer(id) {
  const server = getServer(id);
  if (server.pid) {
    try { process.kill(server.pid, 'SIGTERM'); } catch {}
  }
  const updated = { ...server, status: 'stopped', pid: null };
  saveServer(updated);
  return updated;
}
module.exports = { SUPPORTED_LOADERS, dataDir, jarUrl, createServer, listServers, getServer, startServer, stopServer };