#!/bin/bash
set -eu
export DISPLAY="${DISPLAY:-:99}"
export HIDALGOS_HEADLESS="${HIDALGOS_HEADLESS:-0}"
Xvfb "$DISPLAY" -screen 0 1280x1024x24 -nolisten tcp -ac >/tmp/xvfb.log 2>&1 &
ok=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 0.3
done
if [ "$ok" -ne 1 ]; then
  echo "Xvfb no arranco" >&2
  cat /tmp/xvfb.log >&2 || true
  exit 1
fi
exec python scrapper/rd_hidalgos.py --fresh
