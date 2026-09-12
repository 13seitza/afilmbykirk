#!/usr/bin/env bash
set -euo pipefail

URL="${AFBK_KIOSK_URL:-http://localhost:5000}"
for _attempt in $(seq 1 60); do
  if curl --silent --fail "${URL}/health" >/dev/null; then
    break
  fi
  sleep 1
done

exec chromium "${URL}" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required \
  --start-maximized
