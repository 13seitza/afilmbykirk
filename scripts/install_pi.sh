#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This installer is intended for Raspberry Pi OS."
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${SUDO_USER:-$USER}"
APP_GROUP="$(id -gn "$APP_USER")"
APP_UID="$(id -u "$APP_USER")"
USER_HOME="$(getent passwd "$APP_USER" | cut -d: -f6)"
MEDIA_DIR="${AFBK_MEDIA_DIR:-$USER_HOME/Media/A Film by Kirk}"
PUBLIC_URL="${AFBK_PUBLIC_URL:-http://afilmbykirk.local:5000/}"

echo "Installing A Film by Kirk from $APP_DIR"
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-evdev chromium curl avahi-daemon ffmpeg bluez pulseaudio-utils wtype
sudo raspi-config nonint do_boot_behaviour B4
sudo raspi-config nonint do_blanking 1

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
mkdir -p "$MEDIA_DIR" "$APP_DIR/instance"
if [[ ! -f "$MEDIA_DIR/catalog.json" ]]; then
  cp "$APP_DIR/media.example/catalog.json" "$MEDIA_DIR/catalog.json"
fi

SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
sudo install -m 600 /dev/null /etc/afilmbykirk.env
sudo tee /etc/afilmbykirk.env >/dev/null <<EOF
AFBK_MEDIA_DIR="$MEDIA_DIR"
AFBK_DATABASE="$APP_DIR/instance/afilmbykirk.sqlite3"
AFBK_HOST=0.0.0.0
AFBK_PORT=5000
AFBK_PUBLIC_URL="$PUBLIC_URL"
AFBK_SECRET_KEY="$SECRET_KEY"
AFBK_IDLE_TIMEOUT_SECONDS=600
EOF

sed \
  -e "s|__USER__|$APP_USER|g" \
  -e "s|__GROUP__|$APP_GROUP|g" \
  -e "s|__UID__|$APP_UID|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$APP_DIR/systemd/afilmbykirk.service.in" | sudo tee /etc/systemd/system/afilmbykirk.service >/dev/null

sed \
  -e "s|__USER__|$APP_USER|g" \
  -e "s|__GROUP__|$APP_GROUP|g" \
  -e "s|__APP_DIR__|$APP_DIR|g" \
  "$APP_DIR/systemd/afilmbykirk-remote.service.in" | sudo tee /etc/systemd/system/afilmbykirk-remote.service >/dev/null

AUTOSTART_DIR="$USER_HOME/.config/labwc"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"
LABWC_CONFIG="$AUTOSTART_DIR/rc.xml"
mkdir -p "$AUTOSTART_DIR"
touch "$AUTOSTART_FILE"
python3 "$APP_DIR/scripts/configure_labwc.py" "$LABWC_CONFIG"
KIOSK_COMMAND="$APP_DIR/scripts/start_kiosk.sh &"
if ! grep -Fq "$APP_DIR/scripts/start_kiosk.sh" "$AUTOSTART_FILE"; then
  printf '\n%s\n' "$KIOSK_COMMAND" >> "$AUTOSTART_FILE"
fi
HIDE_CURSOR_COMMAND="wtype -M alt -M logo -P h -p h -m logo -m alt &"
if ! grep -Fq "wtype -M alt -M logo -P h" "$AUTOSTART_FILE"; then
  printf '%s\n' "$HIDE_CURSOR_COMMAND" >> "$AUTOSTART_FILE"
fi
sudo chown -R "$APP_USER:$APP_GROUP" "$AUTOSTART_DIR" "$MEDIA_DIR" "$APP_DIR/instance"

sudo systemctl daemon-reload
sudo systemctl enable --now afilmbykirk.service afilmbykirk-remote.service avahi-daemon bluetooth

echo
echo "Installation complete."
echo "Media folder: $MEDIA_DIR"
echo "Local address: $PUBLIC_URL"
echo "Copy episodes using names such as: S01E01 - Pilot.mp4"
echo "Reboot after confirming Raspberry Pi OS is set to Desktop Autologin."
