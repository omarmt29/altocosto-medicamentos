"""Búsqueda Kielsa (buscador HTTP + detalle vía Meteor DDP/SockJS)."""

from __future__ import annotations

import json
import random
import re
import string
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3
import websocket

from lista import MEDICAMENTOS
from scrapper.ficha import parse_ficha
from scrapper.matching import clasificar, coincide
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_tienda import queries_es, fases_busqueda

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PAUSA = 0.2
TIMEOUT = 35
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def _session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es,es-419;q=0.9,en;q=0.7",
        }
    )
    return s


def buscar_ids(
    s: requests.Session,
    alias: str,
    *,
    buscador: str,
    cache: Path,
    forzar: bool,
) -> tuple[list[str], str, str | None]:
    path = cache_path(cache, alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None
    url = (
        f"{buscador.rstrip('/')}/buscar/"
        f"?product={quote(alias)}"
        f"&categories=%5B%5D"
        f"&page=1"
        f"&orden=relevancia"
    )
    try:
        r = s.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:
        return [], "", str(exc)
    ids = [str(x) for x in (payload.get("results") or []) if x]
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ids, ensure_ascii=False), encoding="utf-8")
    return ids, datetime.now().date().isoformat(), None


def _sockjs_send(ws: websocket.WebSocketApp, obj: dict[str, Any]) -> None:
    raw = json.dumps(obj, separators=(",", ":"))
    ws.send('["' + raw.replace("\\", "\\\\").replace('"', '\\"') + '"]')


def productos_ddp(host: str, ids: list[str], *, timeout: float = 25.0) -> list[dict[str, Any]]:
    if not ids:
        return []
    server = "".join(random.choices(string.digits, k=3))
    session = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    url = f"wss://{host}/sockjs/{server}/{session}/websocket"
    out: dict[str, dict[str, Any]] = {}
    pending = set(ids)
    done = {"ok": False}

    def on_message(ws: websocket.WebSocketApp, message: str) -> None:
        if message == "o":
            _sockjs_send(
                ws,
                {"msg": "connect", "version": "1", "support": ["1", "pre2", "pre1"]},
            )
            return
        if not message.startswith("a"):
            return
        for item in json.loads(message[1:]):
            data = json.loads(item)
            msg = data.get("msg")
            if msg == "connected":
                for i, pid in enumerate(ids):
                    _sockjs_send(
                        ws,
                        {
                            "msg": "sub",
                            "id": f"sub{i}",
                            "name": "product.one",
                            "params": [pid],
                        },
                    )
            elif msg == "added" and data.get("collection") == "product":
                pid = str(data.get("id") or "")
                fields = data.get("fields") or {}
                if pid and fields:
                    out[pid] = fields
                    pending.discard(pid)
            elif msg == "ready":
                done["ok"] = True
                ws.close()

    ws = websocket.WebSocketApp(url, on_message=on_message)
    import threading

    t = threading.Thread(
        target=lambda: ws.run_forever(sslopt={"cert_reqs": 0}),
        daemon=True,
    )
    t.start()
    t0 = time.time()
    while time.time() - t0 < timeout:
        if done["ok"] or not pending:
            break
        time.sleep(0.05)
    try:
        ws.close()
    except Exception:
        pass
    return [{"_id": pid, **fields} for pid, fields in out.items()]


def precio_kielsa(prod: dict[str, Any]) -> float | None:
    for key in ("Precio", "Precio_Todo_Publico"):
        raw = prod.get(key)
        if raw in (None, ""):
            continue
        try:
            n = float(raw)
        except (TypeError, ValueError):
            continue
        if n > 0:
            return n
    return None


def url_producto(site_base: str, prod: dict[str, Any]) -> str:
    """PDP actual de Kielsa (Meteor): /ProductDetails/{_id}."""
    pid = str(prod.get("_id") or "").strip()
    if not pid:
        return site_base.rstrip("/")
    return f"{site_base.rstrip('/')}/ProductDetails/{pid}"


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    site_base: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        nombre = str(prod.get("Articulo_Nombre") or "").strip()
        if not nombre:
            continue
        activo = str(prod.get("Principal_Activo") or "")
        blob = f"{nombre} {activo} {prod.get('Articulo_Descripcion_Completa') or ''}"
        seed_match = seed_match_for_med(blob, pais, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue
        precio = precio_kielsa(prod)
        if not precio:
            continue
        pid = str(prod.get("_id") or prod.get("Articulo_Id") or "")
        if not pid:
            continue
        p_fake = {
            "nombre": nombre,
            "principios_activos": [activo] if activo else [],
            "tipo_presentacion": nombre,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
            obs = f"{obs} | {extra}" if obs else extra
        n_lista = int(med2["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        stock = prod.get("AxB_Existencia") or prod.get("Sumatoria_Zona_unds") or 0
        try:
            qty = int(float(stock))
        except (TypeError, ValueError):
            qty = 0
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": url_producto(site_base, prod),
                "id_producto_farmacia": pid[:80],
                "sku": str(prod.get("Articulo_Id") or pid)[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo") or (activo[:500] if activo else None),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio,
                "moneda": moneda,
                "disponibilidad": "Disponible" if qty > 0 else "Agotado",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    buscador: str,
    site_base: str,
    ddp_host: str,
    cache: Path,
    forzar: bool = False,
    meds: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    s = _session()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        ids_vistos: set[str] = set()
        for fase, aliases in fases_busqueda(pais, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                ids, fecha, err = buscar_ids(s, alias, buscador=buscador, cache=cache, forzar=forzar)
                if err:
                    print(f"  aviso {alias}: {err}")
                    continue
                nuevos = [x for x in ids if x not in ids_vistos]
                ids_vistos.update(nuevos)
                if not nuevos:
                    continue
                time.sleep(PAUSA)
                productos = productos_ddp(ddp_host, nuevos[:16])
                filas.extend(
                    filas_de_productos(
                        med,
                        productos,
                        fecha,
                        vistos,
                        pais=pais,
                        farmacia=farmacia,
                        moneda=moneda,
                        site_base=site_base,
                    )
                )
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
    return filas


def ejecutar(
    *,
    titulo: str,
    pais: str,
    farmacia: str,
    moneda: str,
    buscador: str,
    site_base: str,
    ddp_host: str,
    cache: Path,
    argv: list[str],
) -> int:
    forzar = "--fresh" in argv
    solo_fomac = "--fomac" in argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(titulo)
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    print("=" * 64)
    filas = recolectar(
        pais=pais,
        farmacia=farmacia,
        moneda=moneda,
        buscador=buscador,
        site_base=site_base,
        ddp_host=ddp_host,
        cache=cache,
        forzar=forzar,
        meds=meds,
    )
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos(
            pais,
            farmacia,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    elif not filas:
        print("  aviso: 0 coincidencias — no se purgan filas existentes")
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{pais} {farmacia}: {contar(pais, farmacia)} · total tabla: {contar()}"
    )
    return 0
