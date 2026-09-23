"""Búsqueda WooCommerce Store API compartida para farmacias nuevas."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from lista import MEDICAMENTOS
from scrapper.ficha import parse_ficha
from scrapper.matching import clasificar, coincide
from scrapper.precios import precios_woocommerce
from scrapper.report_seeds import seed_match_for_med
from scrapper.vtex_tienda import fases_busqueda
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos

PAUSA = 0.25
PAGE = 40
MAX_PAGINAS = 4
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str, *, verify: bool = True) -> requests.Session:
    s = requests.Session()
    s.verify = verify
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Referer": base.rstrip("/") + "/",
        }
    )
    return s


def precio_wc(p: dict[str, Any]) -> float | None:
    lista, oferta = precios_woocommerce(p)
    return lista or oferta


def precios_wc(p: dict[str, Any]) -> tuple[float | None, float | None]:
    return precios_woocommerce(p)


def buscar_woo(
    s: requests.Session,
    alias: str,
    *,
    base: str,
    cache: Path,
    forzar: bool,
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(cache, alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    out: list[dict[str, Any]] = []
    vistos: set[int] = set()
    url = base.rstrip("/") + "/wp-json/wc/store/v1/products"
    for page in range(1, MAX_PAGINAS + 1):
        time.sleep(PAUSA)
        try:
            r = s.get(
                url,
                params={"search": alias, "per_page": PAGE, "page": page},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return [], datetime.now().date().isoformat(), str(exc)
        if r.status_code in (401, 403, 429, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        if r.status_code not in (200, 206):
            return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
        try:
            lote = r.json()
        except ValueError:
            return [], datetime.now().date().isoformat(), "respuesta no JSON"
        if not isinstance(lote, list) or not lote:
            break
        for prod in lote:
            pid = int(prod.get("id") or 0)
            if pid and pid not in vistos:
                vistos.add(pid)
                out.append(prod)
        if len(lote) < PAGE:
            break

    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out, datetime.now().date().isoformat(), None


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    *,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        nombre = str(prod.get("name") or "").strip()
        if not nombre:
            continue
        desc = str(prod.get("short_description") or prod.get("description") or "")
        sku = str(prod.get("sku") or prod.get("id") or "").strip()
        blob = " ".join(
            x for x in [nombre, desc, prod.get("slug"), prod.get("permalink"), sku] if x
        )
        seed_match = seed_match_for_med(blob, pais, med)
        if not coincide(blob, med) and not seed_match:
            continue
        precio_lista, precio_oferta = precios_wc(prod)
        precio = precio_lista or precio_oferta
        if not precio:
            continue
        n_lista = int(med["n"])
        clave = (sku or str(prod.get("id") or ""), n_lista)
        if not clave[0] or clave in vistos:
            continue
        vistos.add(clave)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [desc],
            "tipo_presentacion": nombre,
            "laboratorio": "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        ficha = parse_ficha(f"{nombre} {desc}", med2)
        stock = prod.get("is_in_stock")
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": str(prod.get("permalink") or base)[:500],
                "id_producto_farmacia": clave[0][:80],
                "sku": clave[0][:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio,
                "precio_lista": precio_lista or precio,
                "precio_oferta": precio_oferta,
                "moneda": moneda,
                "disponibilidad": "Disponible" if stock not in (False, 0, "0", "false") else "Agotado",
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
    base: str,
    cache: Path,
    forzar: bool = False,
    meds: list[dict[str, Any]] | None = None,
    verify: bool = True,
    solo_cache: bool = False,
) -> list[dict[str, Any]]:
    s = session(base, verify=verify)
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    red_caida = solo_cache
    aviso_red = False
    for med in trabajo:
        n_antes = len(filas)
        for fase, aliases in fases_busqueda(pais, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                path = cache_path(cache, alias)
                if red_caida and not path.exists():
                    continue
                productos, fecha, err = buscar_woo(
                    s, alias, base=base, cache=cache, forzar=False if red_caida else forzar
                )
                if err and not red_caida:
                    bloqueado = (
                        err.startswith("bloqueado")
                        or "timed out" in err.lower()
                        or "timeout" in err.lower()
                    )
                    if bloqueado:
                        red_caida = True
                        if not aviso_red:
                            print(f"  red no disponible ({err}). Sigo con caché local.")
                            aviso_red = True
                    else:
                        print(f"  aviso {alias}: {err}")
                    continue
                filas.extend(
                    filas_de_productos(
                        med,
                        productos,
                        fecha,
                        vistos,
                        pais=pais,
                        farmacia=farmacia,
                        moneda=moneda,
                        base=base,
                    )
                )
                time.sleep(PAUSA)
    return filas


def ejecutar(
    *,
    titulo: str,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
    cache: Path,
    argv: list[str],
    verify: bool = True,
) -> int:
    forzar = "--fresh" in argv
    solo_fomac = "--fomac" in argv
    solo_cache = "--cache" in argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(titulo)
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    if solo_cache:
        print(" Solo caché local (sin red)")
    print("=" * 64)
    filas = recolectar(
        pais=pais,
        farmacia=farmacia,
        moneda=moneda,
        base=base,
        cache=cache,
        forzar=forzar,
        meds=meds,
        verify=verify,
        solo_cache=solo_cache,
    )
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    revisar = len(filas) - ok
    con_precio = sum(1 for f in filas if f.get("precio"))
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar}, con precio={con_precio})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
        if not solo_fomac and not filas:
            print("  aviso: 0 coincidencias — no se purgan filas existentes")
    else:
        borrados = purgar_obsoletos(
            pais,
            farmacia,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · "
        f"obsoletos: {borrados} · "
        f"{pais} {farmacia}: {contar(pais, farmacia)} · "
        f"total tabla: {contar()}"
    )
    return 0
