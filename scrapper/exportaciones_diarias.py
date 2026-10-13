"""Snapshots diarios para consumidores de /api/v1; no consultan fuentes al leer."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "cache" / "api_v1"
ZONA = ZoneInfo("America/Santo_Domingo")
RECURSOS = ("tasas", "purple-book", "ema", "fda")


def ahora():
    return datetime.now(ZONA)


def _json_default(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    raise TypeError(f"No serializable: {type(v).__name__}")


def leer(nombre):
    try:
        return json.loads((CACHE / f"{nombre}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def guardar(nombre, data):
    CACHE.mkdir(parents=True, exist_ok=True)
    fd, temporal = tempfile.mkstemp(dir=CACHE, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=_json_default, allow_nan=False)
        os.replace(temporal, CACHE / f"{nombre}.json")
    finally:
        if os.path.exists(temporal):
            os.unlink(temporal)


def publicar(nombre, filas):
    if not filas:
        raise RuntimeError(f"{nombre}: fuente vacía; se conserva el snapshot anterior")
    guardar(nombre, {"actualizado_en": ahora().isoformat(), "filas": filas})


def actualizar_tasas():
    from generar_comparativo import tasas
    from scrapper.fx import _session
    from scrapper.fuentes_monedas import FUENTES

    fx = tasas(_session())
    filas = []
    for moneda, tasa in fx["por_usd"].items():
        fuente = FUENTES[moneda]
        fila = {"moneda": moneda, "pais": fuente["pais"], "moneda_base": "USD", **tasa}
        fila["es_reserva"] = tasa["fuente"] == "open.er-api.com"
        fila["fuente_datos_url"] = fuente["reserva_url"] if fila["es_reserva"] else fuente["fuente_datos_url"]
        filas.append(fila)
    faltantes = set(FUENTES) - {f["moneda"] for f in filas}
    if faltantes:
        raise RuntimeError(f"Tasas faltantes: {', '.join(sorted(faltantes))}")
    publicar("tasas", filas)


def actualizar_purple():
    from scrapper import fda_purple_book as pb

    ses = pb._session()
    meta = pb.elegir_csv(sess=ses)
    path = pb.descargar_csv(meta, fresh=True, sess=ses)
    filas = pb.filas_para_db(pb.cruzar_con_lista(pb._leer_filas_csv(path)), meta)
    publicar("purple-book", filas)


def actualizar_ema():
    from scrapper import ema_medicines as ema

    path = ema.asegurar_xlsx(fresh=True)
    filas = ema.filas_para_db(ema.cruzar_con_lista(ema.leer_medicines(path)), ahora().date())
    publicar("ema", filas)


def actualizar_fda():
    from lista import MEDICAMENTOS
    from scrapper import fda_openfda_info as fda
    from scrapper.fda_patentes import asegurar_orange_book, asegurar_purple_patents

    purple = leer("purple-book")
    if not purple:
        raise RuntimeError("Debe actualizarse Purple Book antes de FDA")
    ses = fda._session()
    asegurar_orange_book(fresh=True, sess=ses)
    asegurar_purple_patents(fresh=True, sess=ses)
    from concurrent.futures import ThreadPoolExecutor
    from threading import local
    from scrapper.fda_patentes import _leer_ob_txt

    # Tres consultas a la vez para acotar la memoria del contenedor de cron.
    for archivo in ("products.txt", "patent.txt", "exclusivity.txt"):
        _leer_ob_txt(asegurar_orange_book(sess=ses), archivo)
    sesiones = local()
    def construir(med):
        if not hasattr(sesiones, "ses"):
            sesiones.ses = fda._session()
        pb = [f for f in purple["filas"] if f["n_lista"] == int(med["n"])]
        fila = fda.construir_info(med, sesiones.ses, ahora().date(), purple_filas=pb, resolver_anclas=False)
        for key in list(fila):
            if key.endswith("_json"):
                fila[key[:-5]] = fila.pop(key)
        # Fecha del snapshot diario; el periodo original de Purple Book se conserva aparte.
        fila["fecha_dato"] = ahora().date().isoformat()
        fila["fecha_actualizacion"] = ahora().isoformat()
        return fila

    filas = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, fila in enumerate(pool.map(construir, MEDICAMENTOS), 1):
            filas.append(fila)
            print(f"FDA {i}/{len(MEDICAMENTOS)}: {fila['medicamento_lista']}", flush=True)
    publicar("fda", filas)


ACTUALIZADORES = {"tasas": actualizar_tasas, "purple-book": actualizar_purple,
                  "ema": actualizar_ema, "fda": actualizar_fda}


def _actualizar(nombre):
    inicio = ahora().isoformat()
    guardar(f"{nombre}-estado", {"estado": "running", "inicio": inicio})
    try:
        ACTUALIZADORES[nombre]()
        guardar(f"{nombre}-estado", {"estado": "ok", "inicio": inicio, "fin": ahora().isoformat()})
        print(f"Exportación {nombre} actualizada", flush=True)
        return 0
    except Exception as exc:
        guardar(f"{nombre}-estado", {"estado": "error", "inicio": inicio,
                                    "fin": ahora().isoformat(), "error": str(exc)})
        print(f"ERROR exportación {nombre}: {exc}", flush=True)
        return 1


def actualizar(nombre):
    # Evita que un reintento manual pise una actualización del cron.
    import fcntl

    if nombre not in RECURSOS:
        raise ValueError("Fuente desconocida")
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / f"{nombre}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"Exportación {nombre}: ya hay una actualización en curso", flush=True)
            return 1
        return _actualizar(nombre)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", choices=RECURSOS)
    args = ap.parse_args()
    rc = 0
    for nombre in (args.fuente,) if args.fuente else RECURSOS:
        rc |= actualizar(nombre)
    raise SystemExit(rc)
