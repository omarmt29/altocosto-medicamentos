"""Búsqueda compartida para catálogos Next.js estilo Meykos / Cruz Verde GT.

Meykos: GET {base}/api/search?q=
Cruz Verde GT: GET {base}/api/products?search=
"""

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
from scrapper.precios import as_float, pares_lista_oferta
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_tienda import fases_busqueda

PAUSA = 0.25
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str, *, verify: bool = False) -> requests.Session:
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


def _precio_obj(raw: Any) -> float | None:
    """Acepta float o {amount, minorUnit} (centavos)."""
    if isinstance(raw, dict):
        amount = as_float(raw.get("amount"))
        if amount is None:
            return None
        minor = int(raw.get("minorUnit") or 0)
        if minor > 0:
            return amount / (10**minor)
        return amount if amount > 0 else None
    return as_float(raw)


def precios_item(item: dict[str, Any]) -> tuple[float | None, float | None]:
    lista = _precio_obj(item.get("regularPrice")) or _precio_obj(item.get("price"))
    oferta = None
    if item.get("onSale") or item.get("salePrice"):
        oferta = _precio_obj(item.get("salePrice")) or _precio_obj(item.get("price"))
    return pares_lista_oferta(lista, oferta)


def normalizar_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("products") or payload.get("results") or []
        return [x for x in items if isinstance(x, dict)]
    return []


def buscar(
    s: requests.Session,
    alias: str,
    *,
    url: str,
    param: str,
    cache: Path,
    forzar: bool,
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(cache, alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None
    try:
        r = s.get(url, params={param: alias}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 429, 451):
        return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code not in (200, 206):
        return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
    try:
        payload = r.json()
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    productos = normalizar_items(payload)
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def _brand(item: dict[str, Any]) -> str:
    b = item.get("brand")
    if isinstance(b, dict):
        return str(b.get("name") or "")
    return str(b or "")


def _pid(item: dict[str, Any]) -> str:
    for k in ("productId", "id", "key", "sku"):
        v = item.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


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
        pid = _pid(prod)
        if not nombre or not pid:
            continue
        lista, oferta = precios_item(prod)
        if not lista:
            continue
        brand = _brand(prod)
        blob = " ".join(str(x or "") for x in [nombre, brand, prod.get("sku"), prod.get("slug")])
        seed_match = seed_match_for_med(blob, pais, med)
        if not coincide(blob, med) and not seed_match:
            continue
        n_lista = int(med["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [nombre],
            "tipo_presentacion": nombre,
            "laboratorio": brand,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
            obs = f"{obs} | {extra}" if obs else extra
        ficha = parse_ficha(nombre, med2)
        slug = str(prod.get("slug") or "").strip().strip("/")
        url = f"{base.rstrip('/')}/producto/{slug}" if slug else base
        disp = "Disponible" if prod.get("inStock") or prod.get("purchasable") else "Consultar"
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": url[:500],
                "id_producto_farmacia": pid[:80],
                "sku": str(prod.get("sku") or pid)[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio") or (brand or None),
                "precio": lista,
                "precio_lista": lista,
                "precio_oferta": oferta,
                "moneda": moneda,
                "disponibilidad": disp,
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def ejecutar(
    *,
    titulo: str,
    pais: str,
    farmacia: str,
    moneda: str,
    base: str,
    cache: Path,
    api_path: str,
    search_param: str,
    argv: list[str] | None = None,
    verify: bool = False,
) -> int:
    argv = argv or []
    forzar = "--fresh" in argv
    solo_fomac = "--fomac" in argv
    meds = MEDICAMENTOS if not solo_fomac else [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(titulo)
    print("=" * 64)
    s = session(base, verify=verify)
    url = base.rstrip("/") + api_path
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for med in meds:
        for _fase, aliases in fases_busqueda(pais, med):
            for alias in aliases:
                productos, fecha, err = buscar(
                    s, alias, url=url, param=search_param, cache=cache, forzar=forzar
                )
                if err:
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
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = (
        0
        if solo_fomac or not filas
        else purgar_obsoletos(
            pais, farmacia, [(f["id_producto_farmacia"], f["n_lista"]) for f in filas]
        )
    )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{pais} {farmacia}: {contar(pais, farmacia)} · total tabla: {contar()}"
    )
    return 0
