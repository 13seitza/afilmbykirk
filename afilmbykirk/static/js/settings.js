(() => {
  const toast = document.getElementById('settings-toast');
  const volumeStatus = document.getElementById('volume-status');
  const wifiStatus = document.getElementById('wifi-status');
  const wifiList = document.getElementById('wifi-list');
  const remoteReadout = document.getElementById('remote-readout');
  const bluetoothList = document.getElementById('bluetooth-list');
  const backgroundButton = document.getElementById('toggle-background-video');

  const notify = (message) => {
    toast.textContent = message;
    toast.classList.add('visible');
    window.setTimeout(() => toast.classList.remove('visible'), 2600);
  };

  backgroundButton?.addEventListener('click', async () => {
    const enabled = backgroundButton.dataset.enabled !== 'true';
    try {
      const response = await fetch('/api/settings/background-video', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      backgroundButton.dataset.enabled = String(result.enabled);
      backgroundButton.textContent = `Turn ${result.enabled ? 'off' : 'on'}`;
      document.getElementById('background-video-status').textContent =
        `Currently ${result.enabled ? 'on' : 'off'}. When off, the home screen uses the black gradient.`;
      notify(`Background video ${result.enabled ? 'enabled' : 'disabled'}`);
    } catch (error) { notify(error.message); }
  });

  const postVolume = async (action) => {
    const response = await fetch('/api/volume', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    volumeStatus.textContent = `${result.percent}%${result.muted ? ' · Muted' : ''}`;
  };

  document.querySelectorAll('[data-volume]').forEach((button) => {
    button.addEventListener('click', () => postVolume(button.dataset.volume).catch((error) => notify(error.message)));
  });

  const bindAudioOutputs = () => {
    document.querySelectorAll('[data-audio-output]').forEach((button) => {
      button.addEventListener('click', async () => {
        try {
          const response = await fetch('/api/audio/output', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: button.dataset.audioOutput })
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error);
          notify('Audio output selected');
          window.location.reload();
        } catch (error) { notify(error.message); }
      });
    });
  };
  bindAudioOutputs();

  document.getElementById('scan-bluetooth')?.addEventListener('click', async () => {
    bluetoothList.innerHTML = '<p>Searching… Put your speaker in pairing mode.</p>';
    try {
      const response = await fetch('/api/bluetooth');
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      bluetoothList.replaceChildren();
      result.devices.forEach((device) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'wifi-network remote-focus';
        button.innerHTML = '<strong></strong><span>Pair & connect</span>';
        button.querySelector('strong').textContent = device.name;
        button.addEventListener('click', async () => {
          button.disabled = true;
          button.querySelector('span').textContent = 'Connecting…';
          try {
            const paired = await fetch('/api/bluetooth/connect', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ address: device.address })
            });
            const outcome = await paired.json();
            if (!paired.ok) throw new Error(outcome.error);
            notify(`${device.name} connected`);
            window.setTimeout(() => window.location.reload(), 1000);
          } catch (error) {
            button.disabled = false;
            button.querySelector('span').textContent = 'Try again';
            notify(error.message);
          }
        });
        bluetoothList.append(button);
      });
      if (!result.devices.length) bluetoothList.innerHTML = '<p>No devices found. Check pairing mode and scan again.</p>';
    } catch (error) {
      bluetoothList.textContent = '';
      notify(error.message);
    }
  });

  const chooseNetwork = async (network) => {
    const password = network.security === 'Open' ? '' : window.prompt(`Password for ${network.ssid}`);
    if (password === null) return;
    wifiStatus.textContent = `Connecting to ${network.ssid}…`;
    try {
      const response = await fetch('/api/wifi/connect', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid: network.ssid, password })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      wifiStatus.textContent = `Connected to ${result.connected || network.ssid}`;
      notify('Wi-Fi connected');
    } catch (error) {
      wifiStatus.textContent = 'Connection failed';
      notify(error.message);
    }
  };

  document.getElementById('scan-wifi')?.addEventListener('click', async () => {
    wifiList.innerHTML = '<p>Scanning…</p>';
    try {
      const response = await fetch('/api/wifi');
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      wifiStatus.textContent = result.connected ? `Connected to ${result.connected}` : 'Choose a network';
      wifiList.replaceChildren();
      result.networks.forEach((network) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'wifi-network remote-focus';
        button.innerHTML = `<strong></strong><span></span>`;
        button.querySelector('strong').textContent = `${network.connected ? '✓ ' : ''}${network.ssid}`;
        button.querySelector('span').textContent = `${network.signal}% · ${network.security}`;
        button.addEventListener('click', () => chooseNetwork(network));
        wifiList.append(button);
      });
    } catch (error) {
      wifiList.textContent = '';
      notify(error.message);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (remoteReadout) remoteReadout.textContent = `key: ${event.key}  ·  code: ${event.code || 'none'}`;
  }, true);
})();
