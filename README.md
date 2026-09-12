# A Film by Kirk

A cozy, self-contained streaming appliance made as a gift. It discovers locally stored episodes, presents them in a television-friendly Flask/Jinja interface, remembers playback progress, and serves the same library to browsers on the local network.

It works without an internet connection after setup. No episodes, artwork, or other show media are included in Git.

## Features

- Automatic library discovery from names such as `S01E01 - Pilot.mp4`
- Editable titles, descriptions, artwork, and featured episode via `catalog.json`
- Automatic episode thumbnails extracted from video, with in-player frame selection
- Optional full-bleed looping hero video with a cinematic gradient
- Persistent setting to disable the hero video and keep the black gradient
- Season browsing, continue watching, and random episode
- Shared resume progress across TV, phones, and laptops
- Full-screen HDMI playback through Chromium kiosk mode
- LAN streaming with byte-range support for seeking
- QR code for opening the interface on another device
- Keyboard and remote-friendly focus navigation
- Hardware-level mapping for the included XING WEI USB remote's arrows and OK button
- Automatic startup on Raspberry Pi OS
- Black-screen idle mode that wakes on the first remote button
- TV-local Wi-Fi setup, HDMI/Bluetooth audio selection, volume controls, and USB remote diagnostics
- A small Kirk-themed keyboard Easter egg

## Media layout

The reliable cross-device format is MP4 with H.264 video and AAC audio. MKV is indexed, but browser support depends on the codecs inside it; iPhone and iPad are especially likely to require conversion.

```text
~/Media/A Film by Kirk/
├── catalog.json
├── branding/
│   └── hero-background.mp4
├── artwork/
│   ├── s01e01.jpg
│   └── s01e02.jpg
├── Season 01/
│   ├── S01E01 - Pilot.mp4
│   └── S01E02 - The Lorelais First Day at Chilton.mp4
└── Season 02/
    └── S02E01 - Sadie Sadie.mp4
```

Folders are scanned recursively. Every episode filename must contain `SxxExx`. Copy [the example catalog](media.example/catalog.json) into the media folder and expand it with your titles and descriptions. Artwork paths are relative to the media folder.

The included catalog contains titles and descriptions for all 153 episodes. Episode metadata is provided by [TVmaze](https://www.tvmaze.com/shows/525/gilmore-girls/episodeguide) under the CC BY-SA license.

The hero background should be a short, muted, web-friendly MP4. It loops behind a dark gradient and is never required for the app to work.

Episode thumbnails are generated automatically at roughly 25% into each video when first displayed. They also appear on Start/Continue Watching, and the first loaded episode supplies each season tile's artwork. While an episode is paused, choose **Save thumbnail** in the upper-right corner to replace it with the current frame everywhere that episode is used. Generated images live in `generated-artwork/` inside the media folder; an existing catalog image is used until you save a generated replacement.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
./start
```

The first two commands are one-time setup. After that, just run `./start`.
Open [http://127.0.0.1:5000](http://127.0.0.1:5000), add properly named videos to `media/`, and refresh.

### Test the full interface without media

```bash
.venv/bin/python scripts/create_demo_library.py
AFBK_MEDIA_DIR="$PWD/demo-media" AFBK_DATABASE="$PWD/demo-media/demo.sqlite3" .venv/bin/python run.py
```

This creates 153 empty placeholder episodes across seven seasons using the real episode catalog, and seeds a resume card at Season 3, Episode 2. The navigation works normally; video playback remains blank because the generated files contain no media.

## Prepare the Raspberry Pi

Use Raspberry Pi Imager to install the current 64-bit Raspberry Pi OS **with Desktop**. In Imager's customization screen:

1. Set the hostname to `afilmbykirk`.
2. Create your user and password.
3. Add the Wi-Fi network you expect to use.
4. Enable SSH for setup and later maintenance.

The desktop image is used only because the HDMI interface runs in Chromium kiosk mode. The Flask service stays small and the interface has no external assets.

Copy or clone this repository onto the Pi, then run:

```bash
cd /path/to/afilmbykirk
chmod +x scripts/*.sh
./scripts/install_pi.sh
```

Make sure Raspberry Pi OS uses **Desktop Autologin**, then reboot. Current Raspberry Pi OS uses the `labwc` Wayland compositor; the installer adds the kiosk launch to `~/.config/labwc/autostart`.

The installer enables Desktop Autologin and disables Raspberry Pi OS screen blanking. While an episode is playing, the browser also holds a screen wake lock. The display therefore stays awake indefinitely during playback; only paused playback and menu inactivity can trigger the app's black sleep screen.

After reboot:

- The connected TV or projector opens the app automatically.
- Devices on the same Wi-Fi can open `http://afilmbykirk.local:5000/`.
- Episodes live in `~/Media/A Film by Kirk` by default.
- The home-screen Settings link can scan and join Wi-Fi networks, pair a Bluetooth speaker, choose between available HDMI/wired/Bluetooth audio outputs, adjust volume, and identify remote button codes. Wi-Fi passwords require a keyboard for text entry.

Custom install locations are supported:

```bash
AFBK_MEDIA_DIR=/mnt/media AFBK_PUBLIC_URL=http://my-pi.local:5000/ ./scripts/install_pi.sh
```

## Maintenance

```bash
sudo systemctl status afilmbykirk
sudo journalctl -u afilmbykirk -f
sudo systemctl restart afilmbykirk
```

Watch history is stored in `instance/afilmbykirk.sqlite3`. Back up that file to preserve progress.

The interface sleeps after 10 inactive minutes on menus or while playback is paused. Active video prevents sleep. Change the timeout in `/etc/afilmbykirk.env`:

```text
AFBK_IDLE_TIMEOUT_SECONDS=900
```

## Test

```bash
.venv/bin/python -m pytest -q
```

## Planned polish

- Media compatibility report and one-command MP4 conversion
- Richer remote behavior once the actual remote is known
- Special shuffle modes and more show-specific Easter eggs
