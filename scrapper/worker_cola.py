"""Worker de cola de scrapes.

Corre en contenedor aparte (`medicamentos-alto-costo-worker`). Cada job se
ejecuta en un subprocess: si el scraper explota, solo falla ese job; el worker
sigue y la web no se cae.

Uso:
    python scrapper/worker_cola.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from scrapper import jobs_cola as jobs_cola  # noqa: E402
from scrapper.jobs_cola import marcar_fin, reclamar_siguiente, recuperar_stale  # noqa: E402

LOG_DIR = ROOT / "cache" / "jobs"
POLL_SEC = float(os.getenv("JOB_WORKER_POLL_SEC", "3"))
STALE_MIN = int(os.getenv("JOB_WORKER_STALE_MIN", "180"))
JOB_TIMEOUT = int(os.getenv("JOB_WORKER_TIMEOUT_SEC", "7200"))  # 2h


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _fuentes() -> dict:
    """Relee FUENTES del módulo (el worker vive días; el catálogo puede crecer)."""
    import importlib

    importlib.reload(jobs_cola)
    return jobs_cola.FUENTES


def _run_job(job: dict) -> tuple[bool, int | None, str, str]:
    fid = str(job.get("fuente_id") or "")
    meta = _fuentes().get(fid)
    if not meta:
        return False, None, f"Fuente desconocida: {fid}", ""

    script = ROOT / str(meta["script"])
    if not script.exists():
        return False, None, f"Script no encontrado: {script}", ""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    job_id = int(job["id"])
    log_path = LOG_DIR / f"job_{job_id}_{fid}.log"
    argv = list(meta.get("argv") or [])
    cmd = [sys.executable, str(script), *argv]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    started = datetime.now().isoformat(timespec="seconds")
    header = (
        f"# job={job_id} fuente={fid}\n"
        f"# start={started}\n"
        f"# cmd={' '.join(cmd)}\n\n"
    )
    log_path.write_text(header, encoding="utf-8")

    try:
        with log_path.open("a", encoding="utf-8", errors="replace") as logf:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                env=env,
                stdout=logf,
                stderr=subprocess.STDOUT,
                timeout=JOB_TIMEOUT,
                check=False,
            )
        code = int(proc.returncode)
        ok = code == 0
        msg = "OK" if ok else f"exit={code} (ver log)"
        return ok, code, msg, str(log_path.relative_to(ROOT))
    except subprocess.TimeoutExpired:
        msg = f"Timeout tras {JOB_TIMEOUT}s"
        with log_path.open("a", encoding="utf-8") as logf:
            logf.write(f"\n\n# TIMEOUT {msg}\n")
        return False, None, msg, str(log_path.relative_to(ROOT))
    except Exception as exc:
        with log_path.open("a", encoding="utf-8") as logf:
            logf.write("\n\n# EXCEPTION\n")
            logf.write(traceback.format_exc())
        return False, None, str(exc)[:500], str(log_path.relative_to(ROOT))


def loop() -> None:
    wid = _worker_id()
    print(f"Worker cola iniciado · id={wid} · poll={POLL_SEC}s · timeout={JOB_TIMEOUT}s")
    while True:
        try:
            n = recuperar_stale(STALE_MIN)
            if n:
                print(f"Recuperados {n} jobs stale → error")
            job = reclamar_siguiente(wid)
            if not job:
                time.sleep(POLL_SEC)
                continue
            jid = job["id"]
            fid = job["fuente_id"]
            if fid == "farmacias_do":
                print(f"→ job #{jid} farmacias.do excluida")
                marcar_fin(
                    int(jid),
                    ok=False,
                    exit_code=0,
                    mensaje="farmacias.do excluida en este servidor",
                    log_path=None,
                )
                continue
            print(f"→ job #{jid} {fid} …")
            ok, code, msg, log_rel = _run_job(job)
            marcar_fin(jid, ok=ok, exit_code=code, mensaje=msg, log_path=log_rel)
            print(f"← job #{jid} {fid} · {'OK' if ok else 'ERROR'} · {msg}")
        except Exception as exc:
            # Nunca tumbar el loop por un error inesperado de claim/DB
            print(f"Worker loop error: {exc}", file=sys.stderr)
            traceback.print_exc()
            time.sleep(max(5.0, POLL_SEC))


def main() -> int:
    loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
