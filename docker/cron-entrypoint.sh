#!/bin/bash
set -eu

ln -sfn /usr/share/zoneinfo/America/Santo_Domingo /etc/localtime
echo America/Santo_Domingo > /etc/timezone

python - << 'PY'
import os
from pathlib import Path

prefijos = ("REDATAM_", "DB_", "API_", "RETENCION", "TZ", "RUNNING_", "FARMA", "JOB_", "PYTHON", "PATH", "LANG", "LC_", "HIDALGOS_")
lineas = []
for clave in sorted(os.environ):
    if not clave.startswith(prefijos):
        continue
    valor = os.environ[clave].replace("'", "'\\''")
    lineas.append(f"export {clave}='{valor}'")
Path("/etc/altocosto.env").write_text("\n".join(lineas) + "\n")
PY
chmod 600 /etc/altocosto.env

cat > /etc/cron.d/altocosto << 'EOF'
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
CRON_TZ=America/Santo_Domingo
0 0 * * * root /app/docker/run_scrape.sh >> /var/log/alto-costo-cron.log 2>&1

EOF
chmod 644 /etc/cron.d/altocosto
touch /var/log/alto-costo-cron.log

echo "Cron de scrape listo: todos los dias a las 00:00 America/Santo_Domingo"
exec cron -f
