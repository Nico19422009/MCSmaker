const serverList = document.getElementById('serverList');
const details = document.getElementById('serverDetails');
const createForm = document.getElementById('createForm');
const serverNameInput = document.getElementById('serverName');
const serverVersionSelect = document.getElementById('serverVersion');
const formHint = document.getElementById('formHint');

const api = window.mcsmaker || {
  listServers: async () => [
    {
      id: 'demo-1',
      name: 'Demo Realm',
      version: '1.20.1',
      status: 'stopped',
      createdAt: new Date().toISOString(),
      path: '/servers/demo-realm',
      lastStartedAt: null
    }
  ],
  createServer: async () => ({ error: 'Electron API unavailable in browser preview.' }),
  startServer: async () => ({ error: 'Electron API unavailable in browser preview.' }),
  stopServer: async () => ({ error: 'Electron API unavailable in browser preview.' }),
  listVersions: async () => ({ versions: ['1.20.1', '1.20', '1.19.4'] })
};

let servers = [];
let selectedId = null;

const renderServerList = () => {
  serverList.innerHTML = '';

  if (servers.length === 0) {
    const empty = document.createElement('li');
    empty.className = 'server-card';
    empty.innerHTML = '<div class="server-card__info"><h3>No servers yet</h3><p>Create one to get started.</p></div>';
    serverList.appendChild(empty);
    return;
  }

  servers.forEach((server) => {
    const item = document.createElement('li');
    const isActive = server.id === selectedId;
    item.className = `server-card${isActive ? ' server-card--active' : ''}`;
    item.addEventListener('click', () => {
      selectedId = server.id;
      renderServerList();
      renderDetails();
    });

    const playButton = document.createElement('button');
    playButton.className = 'server-card__play';
    playButton.type = 'button';
    playButton.textContent = '▶';
    playButton.addEventListener('click', async (event) => {
      event.stopPropagation();
      const result = await api.startServer(server.id);
      if (result?.error) {
        formHint.textContent = result.error;
        return;
      }
      servers = result?.servers || servers;
      selectedId = server.id;
      formHint.textContent = '';
      renderServerList();
      renderDetails();
    });

    const info = document.createElement('div');
    info.className = 'server-card__info';
    info.innerHTML = `<h3>${server.name}</h3><p>Version ${server.version}</p>`;

    const status = document.createElement('span');
    status.className = `status-pill${server.status === 'running' ? ' status-pill--running' : ''}`;
    status.textContent = server.status === 'running' ? 'Running' : 'Stopped';

    item.appendChild(playButton);
    item.appendChild(info);
    item.appendChild(status);
    serverList.appendChild(item);
  });
};

const renderDetails = () => {
  const server = servers.find((entry) => entry.id === selectedId);
  if (!server) {
    details.innerHTML = `
      <div class="details__empty">
        <h2>Select a server</h2>
        <p>Choose a server from the left list to see details and start it.</p>
      </div>
    `;
    return;
  }

  details.innerHTML = `
    <h2>${server.name}</h2>
    <div class="details__grid">
      <div class="details__item">
        <span>Version</span>
        <strong>${server.version}</strong>
      </div>
      <div class="details__item">
        <span>Status</span>
        <strong>${server.status === 'running' ? 'Running' : 'Stopped'}</strong>
      </div>
      <div class="details__item">
        <span>Folder</span>
        <strong>${server.path}</strong>
      </div>
      <div class="details__item">
        <span>Last started</span>
        <strong>${server.lastStartedAt ? new Date(server.lastStartedAt).toLocaleString() : 'Never'}</strong>
      </div>
    </div>
    <div class="details__actions">
      <button class="primary" id="detailsStart">Start server</button>
      <button class="secondary" id="detailsStop">Stop server</button>
    </div>
  `;

  const startButton = document.getElementById('detailsStart');
  const stopButton = document.getElementById('detailsStop');

  startButton.addEventListener('click', async () => {
    const result = await api.startServer(server.id);
    if (result?.error) {
      formHint.textContent = result.error;
      return;
    }
    servers = result?.servers || servers;
    formHint.textContent = '';
    renderServerList();
    renderDetails();
  });

  stopButton.addEventListener('click', async () => {
    const result = await api.stopServer(server.id);
    if (result?.error) {
      formHint.textContent = result.error;
      return;
    }
    servers = result?.servers || servers;
    formHint.textContent = '';
    renderServerList();
    renderDetails();
  });
};

const loadVersions = async () => {
  const data = await api.listVersions();
  const versions = data?.versions || [];
  serverVersionSelect.innerHTML = '';

  if (versions.length === 0) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No versions available';
    serverVersionSelect.appendChild(option);
    return;
  }

  versions.forEach((version) => {
    const option = document.createElement('option');
    option.value = version;
    option.textContent = version;
    serverVersionSelect.appendChild(option);
  });
};

createForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  formHint.textContent = '';

  const payload = {
    name: serverNameInput.value,
    version: serverVersionSelect.value
  };

  const result = await api.createServer(payload);
  if (result?.error) {
    formHint.textContent = result.error;
    return;
  }

  servers = result?.servers || servers;
  selectedId = result?.server?.id || selectedId;
  serverNameInput.value = '';
  renderServerList();
  renderDetails();
});

const init = async () => {
  await loadVersions();
  servers = await api.listServers();
  if (servers.length > 0) {
    selectedId = servers[0].id;
  }
  renderServerList();
  renderDetails();
};

init();
