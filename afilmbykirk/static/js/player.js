(() => {
  const player = document.getElementById('episode-player');
  if (!player) return;

  const endpoint = `/api/progress/${player.dataset.episodeId}`;
  const controls = document.getElementById('player-controls');
  const playButton = document.getElementById('play-button');
  const thumbnailButton = document.getElementById('thumbnail-button');
  const playerToast = document.getElementById('player-toast');
  const topbar = controls.querySelector('.player-topbar');
  const topbarLinks = [...topbar.querySelectorAll('.remote-focus')];
  const scrubber = document.getElementById('player-scrubber');
  const currentTime = document.getElementById('current-time');
  const durationTime = document.getElementById('duration-time');
  let controlsTimer;
  let lastSent = 0;
  let wakeLock;

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds)) return '0:00';
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainder = total % 60;
    return hours
      ? `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
      : `${minutes}:${String(remainder).padStart(2, '0')}`;
  };

  const showControls = (stayVisible = false) => {
    controls.classList.add('visible');
    window.clearTimeout(controlsTimer);
    if (!stayVisible && !player.paused) {
      controlsTimer = window.setTimeout(() => controls.classList.remove('visible'), 3200);
    }
  };

  const updateControls = () => {
    currentTime.textContent = formatTime(player.currentTime);
    durationTime.textContent = formatTime(player.duration);
    scrubber.value = player.duration ? (player.currentTime / player.duration) * 100 : 0;
    playButton.classList.toggle('is-playing', !player.paused);
    thumbnailButton.hidden = !player.paused;
  };

  const showToast = (message) => {
    playerToast.textContent = message;
    playerToast.classList.add('visible');
    window.setTimeout(() => playerToast.classList.remove('visible'), 2600);
  };

  const seek = (seconds) => {
    player.currentTime = Math.max(0, Math.min(player.duration || Infinity, player.currentTime + seconds));
    updateControls();
    showControls();
  };

  const togglePlayback = () => {
    if (player.paused) player.play();
    else player.pause();
  };

  const keepScreenAwake = async () => {
    if (!('wakeLock' in navigator) || wakeLock) return;
    try {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', () => { wakeLock = undefined; });
    } catch (_error) {
      // Raspberry Pi OS screen blanking is also disabled by the installer.
    }
  };

  const releaseScreen = async () => {
    if (!wakeLock) return;
    await wakeLock.release();
    wakeLock = undefined;
  };

  const save = (completed = false, useBeacon = false) => {
    const body = JSON.stringify({
      position: player.currentTime || 0,
      duration: Number.isFinite(player.duration) ? player.duration : 0,
      completed
    });
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
      return;
    }
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true
    });
  };

  player.addEventListener('loadedmetadata', () => {
    const resumeAt = Number(player.dataset.resumeAt || 0);
    if (resumeAt > 5 && resumeAt < player.duration - 15) player.currentTime = resumeAt;
    updateControls();
  });
  player.addEventListener('play', () => {
    keepScreenAwake();
    updateControls();
    showControls();
  });
  player.addEventListener('pause', () => {
    save();
    releaseScreen();
    updateControls();
    showControls(true);
  });
  player.addEventListener('timeupdate', () => {
    updateControls();
    if (player.currentTime - lastSent >= 10) {
      lastSent = player.currentTime;
      save();
    }
  });
  player.addEventListener('ended', () => {
    save(true);
    releaseScreen();
    showControls(true);
    if (player.dataset.nextUrl) {
      window.setTimeout(() => { window.location.href = player.dataset.nextUrl; }, 1800);
    }
  });
  player.addEventListener('click', () => showControls(player.paused));
  player.addEventListener('mousemove', () => showControls());

  playButton.addEventListener('click', togglePlayback);
  thumbnailButton.addEventListener('click', async () => {
    thumbnailButton.disabled = true;
    thumbnailButton.textContent = 'Saving…';
    try {
      const response = await fetch(`/api/thumbnail/${player.dataset.episodeId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position: player.currentTime })
      });
      if (!response.ok) throw new Error('thumbnail request failed');
      showToast('New episode thumbnail saved');
    } catch (_error) {
      showToast('Could not save thumbnail');
    } finally {
      thumbnailButton.disabled = false;
      thumbnailButton.textContent = '▣ Save thumbnail';
      thumbnailButton.focus();
    }
  });
  scrubber.addEventListener('input', () => {
    if (player.duration) player.currentTime = (Number(scrubber.value) / 100) * player.duration;
    updateControls();
  });

  document.addEventListener('keydown', (event) => {
    const topbarIndex = topbarLinks.indexOf(document.activeElement);
    const usingTopbar = topbarIndex !== -1;

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      showControls(true);
      topbarLinks[0]?.focus();
    } else if (event.key === 'ArrowDown' && usingTopbar) {
      event.preventDefault();
      playButton.focus();
      showControls(player.paused);
    } else if (event.key === 'ArrowLeft' && usingTopbar) {
      event.preventDefault();
      showControls(true);
      topbarLinks[Math.max(0, topbarIndex - 1)]?.focus();
    } else if (event.key === 'ArrowRight' && usingTopbar) {
      event.preventDefault();
      showControls(true);
      topbarLinks[Math.min(topbarLinks.length - 1, topbarIndex + 1)]?.focus();
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      seek(-15);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      seek(15);
    } else if (['Enter', ' ', 'MediaPlayPause', 'Play'].includes(event.key)) {
      if (usingTopbar && ['Enter', ' '].includes(event.key)) {
        event.preventDefault();
        document.activeElement.click();
        return;
      }
      event.preventDefault();
      togglePlayback();
    } else if (['Escape', 'Backspace', 'BrowserBack', 'GoBack'].includes(event.key)) {
      event.preventDefault();
      window.location.href = document.querySelector('.player-topbar a')?.href || '/';
    }
  });

  window.addEventListener('pagehide', () => save(false, true));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && !player.paused) keepScreenAwake();
  });
  if (!player.paused) keepScreenAwake();
  updateControls();
  showControls();
})();
