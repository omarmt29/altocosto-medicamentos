"""Búsqueda MiFarmacia Honduras (Next.js /api/search)."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from lista import MEDICAMENTOS
from scrapper.ficha import parse_ficha
from scrapper.matching import clasificar, coincide
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_tienda import queries_para, fases_busqueda

PAUSA = 0.25
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-HN,es;q=0.9",
            "Referer": base.rstrip("/") + "/",
        }
    )
    return s


def buscar(
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
    url = f"{base.rstrip('/')}/api/search?q={quote(alias)}"
    try:
        r = s.get(url, timeout=TIMEOUT)
        if r.status_code in (401, 403, 429, 451):
            return [], "", f"bloqueado HTTP {r.status_code}"
        r.raise_for_status()
        payload = r.json()
    except requests.RequestException as exc:
        return [], "", str(exc)
    except ValueError:
        return [], "", "respuesta no JSON"
    productos = payload.get("products") if isinstance(payload, dict) else None
    if not isinstance(productos, list):
        productos = []
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def blob_prod(prod: dict[str, Any]) -> str:
    slug = str(prod.get("slug") or "").replace("-", " ")
    return " ".join(
        str(x or "")
        for x in (
            prod.get("name"),
            prod.get("activeIngredients"),
            prod.get("description"),
            prod.get("manufacturer"),
            slug,
        )
    )


def url_pdp(base: str, prod: dict[str, Any]) -> str:
    slug = str(prod.get("slug") or "").strip()
    if slug:
        return f"{base.rstrip('/')}/productos/{slug}"
    return base


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
        blob = blob_prod(prod)
        seed_match = seed_match_for_med(f"{blob} {nombre}", pais, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue
        precio_raw = prod.get("price")
        try:
            precio = float(precio_raw)
        except (TypeError, ValueError):
            precio = 0.0
        if precio <= 0:
            continue
        pid = str(prod.get("id") or prod.get("sku") or prod.get("slug") or "").strip()
        if not pid:
            continue
        stock = prod.get("stock")
        try:
            qty = int(stock) if stock is not None else 1
        except (TypeError, ValueError):
            qty = 1
        p_fake = {
            "nombre": nombre,
            "principios_activos": [prod.get("activeIngredients"), prod.get("manufacturer")],
            "tipo_presentacion": nombre,
            "laboratorio": prod.get("manufacturer"),
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        n_lista = int(med2["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        lab = str(prod.get("manufacturer") or ficha.get("laboratorio") or "").strip()[:200] or None
        principio = ficha.get("principio_activo")
        ing = str(prod.get("activeIngredients") or "").strip()
        if not principio and ing and "empaque" not in ing.lower():
            principio = ing[:500]
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": url_pdp(base, prod),
                "id_producto_farmacia": pid[:80],
                "sku": str(prod.get("sku") or pid)[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": principio,
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": lab,
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


def _cargar_todo_cache(cache: Path) -> list[tuple[list[dict[str, Any]], str]]:
    out: list[tuple[list[dict[str, Any]], str]] = []
    if not cache.exists():
        return out
    for path in sorted(cache.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list) and data:
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            out.append((data, fecha))
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
    solo_cache: bool = False,
) -> list[dict[str, Any]]:
    s = session(base)
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
                if red_caida:
                    path = cache_path(cache, alias)
                    if not path.exists():
                        continue
                    productos, fecha, err = buscar(
                        s, alias, base=base, cache=cache, forzar=False
                    )
                else:
                    productos, fecha, err = buscar(
                        s, alias, base=base, cache=cache, forzar=forzar
                    )
                    if err:
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
                    time.sleep(PAUSA)
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
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
    if red_caida:
        extra = 0
        for productos, fecha in _cargar_todo_cache(cache):
            for med in trabajo:
                n0 = len(filas)
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
                extra += len(filas) - n0
        if extra:
            print(f"  +{extra} SKU extra al rematar todo el caché")
        hoy = datetime.now().date().isoformat()
        for f in filas:
            f["fecha_dato"] = hoy
            obs = str(f.get("observacion") or "").strip()
            nota = "PVP rematado desde caché local (red bloqueada)"
            if nota not in obs:
                f["observacion"] = f"{obs} | {nota}" if obs else nota
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
    if solo_fomac:
        borrados = 0
    elif not filas:
        borrados = 0
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
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0
