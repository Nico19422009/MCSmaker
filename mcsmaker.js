#!/usr/bin/env node
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const readline = require('readline/promises');
const { stdin, stdout } = require('process');
const { spawn, spawnSync } = require('child_process');
const { Readable } = require('stream');
const { pipeline } = require('stream/promises');

const APP_VERSION = '1.6.0';
const LOADERS = ['vanilla', 'paper', 'fabric', 'forge'];
const HOME = process.env.MCSMAKER_HOME ||
  path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'), 'mcsmaker');
const SERVERS_DIR = path.join(HOME, 'servers');
const BACKUPS_DIR = path.join(HOME, 'backups');
const STORE_FILE = path.join(HOME, 'servers.json');

const rl = readline.createInterface({ input: stdin, output: stdout });
const colors = {
  reset: '\x1b[0m', cyan: '\x1b[36m', green: '\x1b[32m',
  yellow: '\x1b[33m', red: '\x1b[31m', dim: '\x1b[2m', bold: '\x1b[1m'
};
const color = (name, text) => stdout.isTTY ? colors[name] + text + colors.reset : text;
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function clear() {
  if (stdout.isTTY) console.clear();
}
function banner() {
  console.log(color('cyan', [
    ' __  __  ____ ____  __  __       _             ',
    '|  \/  |/ ___/ ___||  \/  | __ _| | _____ _ __ ',
    '| |\/| | |   \\___ \\| |\/| |/ _` | |/ / _ \\ \__|',
    '| |  | | |___ ___) | |  | | (_| |   <  __/ |   ',
    '|_|  |_|\\____|____/|_|  |_|\\__,_|_|\\_\\___|_|   '
  ].join('\n')));
  console.log(color('dim', 'Linux Minecraft Server Manager v' + APP_VERSION));
  console.log();
}
function ensureDirs() {
  fs.mkdirSync(SERVERS_DIR, { recursive: true });
  fs.mkdirSync(BACKUPS_DIR, { recursive: true });
}
function readStore() {
  ensureDirs();
  try {
    const data = JSON.parse(fs.readFileSync(STORE_FILE, 'utf8'));
    return Array.isArray(data.servers) ? data : { servers: [] };
  } catch {
    return { servers: [] };
  }
}
function writeStore(store) {
  ensureDirs();
  fs.writeFileSync(STORE_FILE, JSON.stringify(store, null, 2) + '\n');
}
function safeName(value) {
  const result = String(value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_');
  if (!result || result === '.' || result === '..') throw new Error('Ungültiger Servername.');
  return result;
}
function isRunning(server) {
  if (!server.pid) return false;
  try {
    process.kill(server.pid, 0);
    return true;
  } catch {
    return false;
  }
}
function normalizedServers() {
  const store = readStore();
  let changed = false;
  store.servers = store.servers.map(server => {
    const running = isRunning(server);
    if (!running && server.pid) {
      changed = true;
      return { ...server, pid: null, status: 'stopped' };
    }
    return { ...server, status: running ? 'running' : 'stopped' };
  });
  if (changed) writeStore(store);
  return store.servers;
}
function saveServer(updated) {
  const store = readStore();
  const index = store.servers.findIndex(server => server.id === updated.id);
  if (index < 0) throw new Error('Server wurde nicht gefunden.');
  store.servers[index] = updated;
  writeStore(store);
}
function mcutilsUrl(loader, version) {
  loader = String(loader || '').toLowerCase();
  version = String(version || '').trim();
  if (!LOADERS.includes(loader)) throw new Error('Unbekannte Server-Software.');
  if (!/^[0-9A-Za-z._-]+$/.test(version)) throw new Error('Ungültige Minecraft-Version.');
  return 'https://mcutils.com/api/server-jars/' + loader + '/' + version + '/download';
}
async function downloadFile(url, destination) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok || !response.body) throw new Error('Download fehlgeschlagen: HTTP ' + response.status);
  const temp = destination + '.download';
  try {
    await pipeline(Readable.fromWeb(response.body), fs.createWriteStream(temp));
    fs.renameSync(temp, destination);
  } catch (error) {
    fs.rmSync(temp, { force: true });
    throw error;
  }
}
async function pause() {
  await rl.question('\n' + color('dim', 'Enter drücken, um zurückzugehen...'));
}
async function askRequired(question) {
  while (true) {
    const value = (await rl.question(question)).trim();
    if (value) return value;
    console.log(color('red', 'Dieses Feld darf nicht leer sein.'));
  }
}
async function selectLoader() {
  console.log();
  LOADERS.forEach((loader, index) => console.log('  ' + (index + 1) + ') ' + loader));
  while (true) {
    const value = Number(await rl.question('\nServer-Software: '));
    if (value >= 1 && value <= LOADERS.length) return LOADERS[value - 1];
    console.log(color('red', 'Bitte 1 bis ' + LOADERS.length + ' wählen.'));
  }
}
async function selectServer(question = 'Server wählen: ') {
  const servers = normalizedServers();
  if (!servers.length) {
    console.log(color('yellow', 'Noch keine Server vorhanden.'));
    return null;
  }
  console.log();
  servers.forEach((server, index) => {
    const state = server.status === 'running' ? color('green', 'läuft') : color('red', 'gestoppt');
    console.log('  ' + (index + 1) + ') ' + server.name + '  [' + server.loader + ' ' + server.version + ']  ' + state);
  });
  console.log('  0) Abbrechen');
  while (true) {
    const value = Number(await rl.question('\n' + question));
    if (value === 0) return null;
    if (value >= 1 && value <= servers.length) return servers[value - 1];
    console.log(color('red', 'Ungültige Auswahl.'));
  }
}
async function createServerMenu() {
  clear(); banner();
  console.log(color('bold', 'NEUEN SERVER ERSTELLEN\n'));
  const name = safeName(await askRequired('Servername: '));
  const version = await askRequired('Minecraft-Version (z.B. 1.21.8): ');
  const loader = await selectLoader();
  let memory = (await rl.question('RAM (Standard 2G): ')).trim().toUpperCase() || '2G';
  if (!/^\d+[MG]$/.test(memory)) throw new Error('RAM muss wie 2G oder 4096M aussehen.');

  const store = readStore();
  if (store.servers.some(server => server.name.toLowerCase() === name.toLowerCase())) {
    throw new Error('Ein Server mit diesem Namen existiert schon.');
  }
  console.log('\nQuelle: ' + mcutilsUrl(loader, version));
  const eula = (await rl.question('Akzeptierst du die Minecraft EULA? (ja/nein): ')).trim().toLowerCase();
  if (!['ja', 'j', 'yes', 'y'].includes(eula)) {
    console.log(color('yellow', 'Abgebrochen. Ohne EULA wird kein Server erstellt.'));
    return;
  }

  const serverDir = path.join(SERVERS_DIR, name);
  fs.mkdirSync(serverDir, { recursive: true });
  const jar = path.join(serverDir, 'server.jar');
  console.log(color('cyan', '\nJAR wird von mcutils heruntergeladen...'));
  try {
    await downloadFile(mcutilsUrl(loader, version), jar);
  } catch (error) {
    fs.rmSync(serverDir, { recursive: true, force: true });
    throw error;
  }
  fs.writeFileSync(path.join(serverDir, 'eula.txt'), 'eula=true\n');
  fs.writeFileSync(path.join(serverDir, 'server.properties'), 'server-port=25565\nmotd=MCSMaker Server\n');

  const server = {
    id: crypto.randomUUID(), name, version, loader, memory,
    path: serverDir, jar, pid: null, status: 'stopped',
    createdAt: new Date().toISOString(), lastStartedAt: null
  };
  store.servers.push(server);
  writeStore(store);
  console.log(color('green', '\nServer wurde erstellt: ' + serverDir));
}
async function listMenu() {
  clear(); banner();
  console.log(color('bold', 'SERVERLISTE\n'));
  const servers = normalizedServers();
  if (!servers.length) {
    console.log(color('yellow', 'Noch keine Server vorhanden.'));
    return;
  }
  for (const server of servers) {
    const state = server.status === 'running' ? color('green', 'LÄUFT') : color('red', 'GESTOPPT');
    console.log(color('bold', server.name) + '  ' + state);
    console.log('  Software: ' + server.loader + ' ' + server.version);
    console.log('  RAM:      ' + server.memory);
    console.log('  PID:      ' + (server.pid || '-'));
    console.log('  Ordner:   ' + server.path);
    console.log();
  }
}
async function startMenu() {
  clear(); banner();
  console.log(color('bold', 'SERVER STARTEN'));
  const server = await selectServer();
  if (!server) return;
  if (isRunning(server)) {
    console.log(color('yellow', '\nDer Server läuft bereits.'));
    return;
  }
  if (!fs.existsSync(server.jar)) throw new Error('server.jar fehlt in ' + server.path);
  if (spawnSync('java', ['-version'], { stdio: 'ignore' }).status !== 0) {
    throw new Error('Java wurde nicht gefunden. Installiere die passende Java-Version.');
  }
  const logsDir = path.join(server.path, 'logs');
  fs.mkdirSync(logsDir, { recursive: true });
  const logFd = fs.openSync(path.join(logsDir, 'mcsmaker.log'), 'a');
  const child = spawn('java', ['-Xms' + server.memory, '-Xmx' + server.memory, '-jar', 'server.jar', 'nogui'], {
    cwd: server.path, detached: true, stdio: ['ignore', logFd, logFd]
  });
  child.unref();
  const updated = { ...server, pid: child.pid, status: 'running', lastStartedAt: new Date().toISOString() };
  saveServer(updated);
  await sleep(700);
  if (!isRunning(updated)) throw new Error('Server ist direkt abgestürzt. Prüfe die Logs.');
  console.log(color('green', '\n' + server.name + ' läuft. PID: ' + child.pid));
}
async function stopMenu() {
  clear(); banner();
  console.log(color('bold', 'SERVER STOPPEN'));
  const server = await selectServer();
  if (!server) return;
  if (!isRunning(server)) {
    console.log(color('yellow', '\nDer Server ist bereits gestoppt.'));
    return;
  }
  process.kill(server.pid, 'SIGTERM');
  saveServer({ ...server, pid: null, status: 'stopped' });
  console.log(color('green', '\n' + server.name + ' wurde gestoppt.'));
}
async function logsMenu() {
  clear(); banner();
  console.log(color('bold', 'LETZTE LOGS'));
  const server = await selectServer();
  if (!server) return;
  const logFile = path.join(server.path, 'logs', 'mcsmaker.log');
  if (!fs.existsSync(logFile)) {
    console.log(color('yellow', '\nNoch keine Logs vorhanden.'));
    return;
  }
  const lines = fs.readFileSync(logFile, 'utf8').split(/\r?\n/).slice(-40);
  console.log('\n' + lines.join('\n'));
}
async function backupMenu() {
  clear(); banner();
  console.log(color('bold', 'BACKUP ERSTELLEN'));
  const server = await selectServer();
  if (!server) return;
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const destination = path.join(BACKUPS_DIR, server.name + '-' + stamp);
  console.log(color('cyan', '\nBackup wird erstellt...'));
  fs.cpSync(server.path, destination, { recursive: true });
  console.log(color('green', 'Backup gespeichert: ' + destination));
}
async function deleteMenu() {
  clear(); banner();
  console.log(color('bold', 'SERVER LÖSCHEN'));
  const server = await selectServer();
  if (!server) return;
  if (isRunning(server)) throw new Error('Stoppe den Server zuerst.');
  const confirm = await rl.question(color('red', '\n"' + server.name + '" wirklich komplett löschen? Tippe LÖSCHEN: '));
  if (confirm !== 'LÖSCHEN') {
    console.log(color('yellow', 'Abgebrochen.'));
    return;
  }
  fs.rmSync(server.path, { recursive: true, force: true });
  const store = readStore();
  store.servers = store.servers.filter(entry => entry.id !== server.id);
  writeStore(store);
  console.log(color('green', 'Server wurde gelöscht.'));
}
async function systemCheckMenu() {
  clear(); banner();
  console.log(color('bold', 'SYSTEMCHECK\n'));
  const nodeVersion = process.version;
  const java = spawnSync('java', ['-version'], { encoding: 'utf8' });
  const javaText = (java.stderr || java.stdout || 'nicht gefunden').split(/\r?\n/)[0];
  const disk = fs.statfsSync(HOME);
  const freeGiB = (Number(disk.bavail) * Number(disk.bsize) / 1024 ** 3).toFixed(1);
  console.log('Betriebssystem: ' + os.type() + ' ' + os.release());
  console.log('Architektur:    ' + os.arch());
  console.log('Node.js:        ' + nodeVersion);
  console.log('Java:           ' + javaText);
  console.log('Freier Speicher:' + ' ' + freeGiB + ' GiB');
  console.log('Datenordner:    ' + HOME);
}
async function mainMenu() {
  while (true) {
    clear(); banner();
    console.log('  1) Neuen Server erstellen');
    console.log('  2) Server starten');
    console.log('  3) Server stoppen');
    console.log('  4) Serverliste und Status');
    console.log('  5) Logs anzeigen');
    console.log('  6) Backup erstellen');
    console.log('  7) Server löschen');
    console.log('  8) Systemcheck');
    console.log('  0) Beenden');
    const choice = (await rl.question('\nAuswahl: ')).trim();
    try {
      if (choice === '0') break;
      if (choice === '1') await createServerMenu();
      else if (choice === '2') await startMenu();
      else if (choice === '3') await stopMenu();
      else if (choice === '4') await listMenu();
      else if (choice === '5') await logsMenu();
      else if (choice === '6') await backupMenu();
      else if (choice === '7') await deleteMenu();
      else if (choice === '8') await systemCheckMenu();
      else {
        console.log(color('red', 'Ungültige Auswahl.'));
        await sleep(700);
        continue;
      }
    } catch (error) {
      console.log(color('red', '\nFehler: ' + error.message));
    }
    await pause();
  }
  rl.close();
  console.log('\nBis dann.');
}

ensureDirs();
mainMenu().catch(error => {
  console.error(color('red', 'Fehler: ' + error.message));
  rl.close();
  process.exitCode = 1;
});
