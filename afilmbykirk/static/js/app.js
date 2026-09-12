(() => {
  const idleSeconds = Number(document.body.dataset.idleTimeout || 600);
  const sleepScreen = document.getElementById('sleep-screen');
  const volumeToast = document.getElementById('volume-toast');
  let idleTimer;
  let sleeping = false;

  const videoIsPlaying = () => {
    const player = document.querySelector('video:not(.ambient-video)');
    return player && !player.paused && !player.ended;
  };

  const enterSleep = () => {
    if (videoIsPlaying()) return;
    sleeping = true;
    document.body.classList.add('is-sleeping');
    sleepScreen?.setAttribute('aria-hidden', 'false');
  };

  const scheduleSleep = () => {
    window.clearTimeout(idleTimer);
    if (!sleeping && idleSeconds > 0 && !videoIsPlaying()) {
      idleTimer = window.setTimeout(enterSleep, idleSeconds * 1000);
    }
  };

  const wake = (event) => {
    if (sleeping) {
      sleeping = false;
      document.body.classList.remove('is-sleeping');
      sleepScreen?.setAttribute('aria-hidden', 'true');
      if (event.type !== 'mousemove') {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }
    scheduleSleep();
  };

  document.addEventListener('keydown', (event) => {
    const volumeActions = {
      AudioVolumeUp: 'up',
      AudioVolumeDown: 'down',
      AudioVolumeMute: 'mute',
      VolumeUp: 'up',
      VolumeDown: 'down',
      VolumeMute: 'mute'
    };
    const volumeAction = volumeActions[event.key];
    if (volumeAction && document.body.dataset.localControls === 'true') {
      event.preventDefault();
      event.stopImmediatePropagation();
      fetch('/api/volume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: volumeAction })
      }).then((response) => response.json().then((result) => ({ response, result })))
        .then(({ response, result }) => {
          if (!response.ok) throw new Error(result.error);
          volumeToast.textContent = result.muted ? 'Muted' : `Volume ${result.percent}%`;
          volumeToast.classList.add('visible');
          window.setTimeout(() => volumeToast.classList.remove('visible'), 1400);
        }).catch(() => {});
      scheduleSleep();
      return;
    }
    if (!sleeping && ['Sleep', 'PowerOff'].includes(event.key)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      enterSleep();
      return;
    }
    wake(event);
  }, true);
  document.addEventListener('pointerdown', wake, true);
  document.addEventListener('touchstart', wake, { capture: true, passive: false });
  document.addEventListener('mousemove', wake, { passive: true });

  const focusables = () =>
    [...document.querySelectorAll('.remote-focus:not([disabled])')]
      .filter((item) => item.offsetParent !== null);

  const center = (element) => {
    const box = element.getBoundingClientRect();
    return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
  };

  const moveFocus = (direction) => {
    const items = focusables();
    if (!items.length) return;
    if (!items.includes(document.activeElement)) {
      items[0].focus();
      return;
    }

    const current = document.activeElement;
    const origin = center(current);
    const horizontal = direction === 'left' || direction === 'right';
    const candidates = items
      .filter((item) => item !== current)
      .map((item) => {
        const point = center(item);
        const dx = point.x - origin.x;
        const dy = point.y - origin.y;
        const valid = direction === 'left' ? dx < -4
          : direction === 'right' ? dx > 4
          : direction === 'up' ? dy < -4
          : dy > 4;
        const primary = horizontal ? Math.abs(dx) : Math.abs(dy);
        const cross = horizontal ? Math.abs(dy) : Math.abs(dx);
        return { item, valid, score: primary + cross * 2.5 };
      })
      .filter((candidate) => candidate.valid)
      .sort((a, b) => a.score - b.score);

    if (candidates[0]) {
      candidates[0].item.focus();
      candidates[0].item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  };

  // Some USB media remotes expose their direction pad as a tiny mouse rather
  // than keyboard arrows. Convert deliberate pointer travel into the same key
  // events used by the rest of the remote navigation system.
  if (document.body.dataset.localControls === 'true') {
    let previousPointer;
    let lastPointerNavigation = 0;
    let accumulatedX = 0;
    let accumulatedY = 0;
    document.addEventListener('mousemove', (event) => {
      const current = { x: event.clientX, y: event.clientY };
      if (!previousPointer) {
        previousPointer = current;
        return;
      }
      const dx = current.x - previousPointer.x;
      const dy = current.y - previousPointer.y;
      previousPointer = current;
      accumulatedX += dx;
      accumulatedY += dy;
      if (Date.now() - lastPointerNavigation < 140) return;
      if (Math.max(Math.abs(accumulatedX), Math.abs(accumulatedY)) < 4) return;
      const key = Math.abs(accumulatedX) > Math.abs(accumulatedY)
        ? (accumulatedX > 0 ? 'ArrowRight' : 'ArrowLeft')
        : (accumulatedY > 0 ? 'ArrowDown' : 'ArrowUp');
      lastPointerNavigation = Date.now();
      accumulatedX = 0;
      accumulatedY = 0;
      document.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
    }, { passive: true });
  }

  document.addEventListener('keydown', (event) => {
    if (document.body.classList.contains('watch-page')) return;
    if (
      event.key === 'ArrowDown'
      && document.body.classList.contains('home-page')
      && document.activeElement?.classList.contains('feature-card')
    ) {
      event.preventDefault();
      document.querySelector('.season-tile')?.focus();
      return;
    }

    if (
      event.key === 'ArrowUp'
      && document.body.classList.contains('home-page')
      && document.activeElement?.classList.contains('season-tile')
    ) {
      event.preventDefault();
      const originX = center(document.activeElement).x;
      const nearestFeature = [...document.querySelectorAll('.feature-card')]
        .sort((a, b) => Math.abs(center(a).x - originX) - Math.abs(center(b).x - originX))[0];
      nearestFeature?.focus();
      return;
    }

    const firstEpisode = document.querySelector('.episode-list .episode-row:first-child');
    if (
      event.key === 'ArrowUp'
      && document.body.classList.contains('season-page')
      && document.activeElement === firstEpisode
    ) {
      event.preventDefault();
      document.querySelector('.play-season-button')?.focus();
      return;
    }

    const directions = {
      ArrowLeft: 'left',
      ArrowRight: 'right',
      ArrowUp: 'up',
      ArrowDown: 'down'
    };

    if (directions[event.key]) {
      event.preventDefault();
      moveFocus(directions[event.key]);
      return;
    }

    if (['Escape', 'Backspace', 'BrowserBack', 'GoBack'].includes(event.key)) {
      const backLink = document.querySelector(
        '.player-heading .quiet-link, .season-actions .back-button'
      );
      if (!backLink) return;
      event.preventDefault();
      window.location.href = backLink.href;
      return;
    }

    if (['MediaPlayPause', 'Play'].includes(event.key) && document.activeElement?.click) {
      event.preventDefault();
      document.activeElement.click();
    }
  });

  window.addEventListener('load', () => {
    if (document.body.classList.contains('home-page')) {
      document.querySelector('.continue-card')?.focus();
    } else if (document.body.classList.contains('season-page')) {
      document.querySelector('.play-season-button')?.focus();
    }
    scheduleSleep();
  });

  const player = document.querySelector('video:not(.ambient-video)');
  player?.addEventListener('play', () => window.clearTimeout(idleTimer));
  player?.addEventListener('pause', scheduleSleep);
  player?.addEventListener('ended', scheduleSleep);

  let secret = '';
  document.addEventListener('keypress', (event) => {
    secret = (secret + event.key.toLowerCase()).slice(-4);
    if (secret === 'kirk') {
      const toast = document.getElementById('kirk-toast');
      toast.classList.add('visible');
      document.body.classList.toggle('kirk-mode');
      setTimeout(() => toast.classList.remove('visible'), 2600);
    }
  });
})();
