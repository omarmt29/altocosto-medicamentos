#!/usr/bin/env bash
# Corrida diaria completa: scrapers del contenedor principal + Hidalgos (Playwright) al final.
#
# Uso:
#   bash scrapper/run_cron_diario.sh
#   bash scrapper/run_cron_diario.sh --fresh
#
# Crontab (ejemplo, 06:15):
#   15 6 * * * /bin/bash /home/dev/medicamentos_alto_costo/scrapper/run_cron_diario.sh --fresh >> /var/log/alto-costo-cron.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMG_MAIN="${ALTO_COSTO_IMG_MAIN:-medicamentos-alto-costo}"
IMG_PW="${ALTO_COSTO_IMG_HIDALGOS:-extraccion-medicamentos_extraccion-medicamentos}"
FLAGS=("$@")

echo "=== [1/2] Scrapers principales ($IMG_MAIN) ==="
set +e
docker exec -w /app "$IMG_MAIN" python scrapper/cron_diario.py --sin-hidalgos "${FLAGS[@]}"
RC_MAIN=$?
set -e

echo "=== [2/2] Los Hidalgos ($IMG_PW, Playwright) ==="
set +e
docker run --rm --memory=3g \
  --env-file "$ROOT/.env" \
  -v "$ROOT:/tmp/mac" \
  -w /tmp/mac \
  -e PYTHONPATH=/tmp/mac \
  "$IMG_PW" \
  python scrapper/rd_hidalgos.py "${FLAGS[@]}"
RC_HID=$?
set -e

echo "=== Registrando Hidalgos en log de cron (exit=$RC_HID) ==="
docker exec -w /app "$IMG_MAIN" python scrapper/cron_diario.py --registrar-hidalgos "$RC_HID"

if [[ "$RC_MAIN" -ne 0 || "$RC_HID" -ne 0 ]]; then
  echo "=== Cron diario con errores (main=$RC_MAIN hidalgos=$RC_HID) ==="
  exit 1
fi
echo "=== Cron diario OK ==="
