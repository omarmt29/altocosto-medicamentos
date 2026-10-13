#!/bin/bash
set -eu
set -a
# shellcheck disable=SC1091
. /etc/altocosto.env
set +a
cd /app
echo "=== scrape $(date -Is) ==="
exec 9>/tmp/altocosto-scrape.lock
if ! flock -n 9; then
  echo "Ya hay un scrape en curso; esta corrida se omite."
  exit 0
fi

set +e
python scrapper/cron_diario.py --sin-hidalgos --fresh
RC_MAIN=$?
set -e
echo "=== Scrapers principales exit=${RC_MAIN} ==="

IMG="${HIDALGOS_IMAGE:-altocosto-playwright}"
NET="${HIDALGOS_NETWORK:-altocosto-medicamentos_default}"
ROOT="${HIDALGOS_HOST_ROOT:-/var/www/altocosto-medicamentos}"

echo "=== Los Hidalgos (${IMG}) ==="
set +e
docker run --rm \
  --network "$NET" \
  --memory=512m \
  --memory-swap=1024m \
  --shm-size=128m \
  --oom-score-adj=500 \
  --env-file /app/.env \
  -e RUNNING_IN_CONTAINER=1 \
  -e DB_DIALECT=postgres \
  -e REDATAM_DB_HOST=postgres \
  -e REDATAM_DB_PORT=5432 \
  -e REDATAM_DB_SCHEMA=public \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONPATH=/app \
  -v "${ROOT}:/app" \
  -e HIDALGOS_HEADLESS=0 \
  -w /app \
  "$IMG" \
  bash /app/docker/hidalgos-entry.sh
RC_HID=$?
set -e
echo "=== Hidalgos exit=${RC_HID} ==="

set +e
python scrapper/cron_diario.py --registrar-hidalgos "$RC_HID"
set -e

if [ "$RC_MAIN" -ne 0 ] || [ "$RC_HID" -ne 0 ]; then
  echo "=== Cron diario con errores (main=${RC_MAIN} hidalgos=${RC_HID}) ==="
  exit 1
fi
echo "=== Cron diario OK ==="
