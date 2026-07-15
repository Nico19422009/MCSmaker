#!/usr/bin/env node
const manager = require('../src/core/server-manager');

const [, , command, ...args] = process.argv;
const help = () => console.log(`MCSmaker CLI

  mcsmaker list
  mcsmaker create <name> <version> [vanilla|paper|fabric|forge] [2G]
  mcsmaker start <id>
  mcsmaker stop <id>
  mcsmaker url <loader> <version>

Data: ${manager.dataDir()}`);

(async () => {
  try {
    if (command === 'list') {
      const servers = manager.listServers();
      if (!servers.length) return console.log('No servers yet.');
      for (const s of servers) console.log(`${s.id}\t${s.name}\t${s.loader} ${s.version}\t${s.status}\t${s.path}`);
    } else if (command === 'create') {
      const [name, version, loader, memory] = args;
      const server = await manager.createServer({ name, version, loader, memory });
      console.log(`Created ${server.name} (${server.loader} ${server.version})\n${server.path}`);
    } else if (command === 'start') {
      const server = manager.startServer(args[0]);
      console.log(`Started ${server.name} (PID ${server.pid})`);
    } else if (command === 'stop') {
      const server = manager.stopServer(args[0]);
      console.log(`Stopped ${server.name}`);
    } else if (command === 'url') {
      console.log(manager.jarUrl(args[0], args[1]));
    } else help();
  } catch (error) {
    console.error('Error:', error.message);
    process.exitCode = 1;
  }
})();