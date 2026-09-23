"""Búsqueda Magento 2 GraphQL (Farmacias del Ahorro y similares)."""

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
from scrapper.precios import precios_magento
from scrapper.report_seeds import seed_match_for_med
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos
from scrapper.vtex_tienda import queries_es, fases_busqueda

PAUSA = 0.25
PAGE = 20
MAX_PAGINAS = 4
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

GQL = """
query Search($q: String!, $page: Int!, $size: Int!) {
  products(search: $q, currentPage: $page, pageSize: $size) {
    total_count
    items {
      sku
      name
      url_key
      stock_status
      price_range {
        minimum_price {
          regular_price { value currency }
          final_price { value currency }
        }
      }
    }
  }
}
"""


def cache_path(cache: Path, alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return cache / f"{safe}.json"


def session(base: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.7",
            "Origin": base.rstrip("/"),
            "Referer": base.rstrip("/") + "/",
            "Store": "default",
        }
    )
    return s


def _precio(item: dict[str, Any]) -> float | None:
    """Precio de lista (regular_price); fallback a final/promo."""
    lista, oferta = precios_magento(item)
    return lista or oferta


def _precios(item: dict[str, Any]) -> tuple[float | None, float | None]:
    return precios_magento(item)


def buscar_magento(
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

    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    gql_url = base.rstrip("/") + "/graphql"
    for pagina in range(1, MAX_PAGINAS + 1):
        time.sleep(PAUSA)
        try:
            r = s.post(
                gql_url,
                json={"query": GQL, "variables": {"q": alias, "page": pagina, "size": PAGE}},
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            return [], datetime.now().date().isoformat(), str(exc)
        if r.status_code in (401, 403, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        if r.status_code not in (200, 206):
            return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
        try:
            payload = r.json()
        except ValueError:
            return [], datetime.now().date().isoformat(), "respuesta no JSON"
        if payload.get("errors"):
            msg = str(payload["errors"][0].get("message") or payload["errors"][0])[:200]
            return [], datetime.now().date().isoformat(), f"graphql {msg}"
        bloque = (payload.get("data") or {}).get("products") or {}
        lote = bloque.get("items") or []
        if not isinstance(lote, list) or not lote:
            break
        for prod in lote:
            sku = str(prod.get("sku") or "")
            if not sku or sku in vistos:
                continue
            vistos.add(sku)
            productos.append(prod)
        total = int(bloque.get("total_count") or 0)
        if len(productos) >= total or len(lote) < PAGE:
            break

    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def url_pdp(base: str, prod: dict[str, Any]) -> str:
    slug = str(prod.get("url_key") or "").strip().strip("/")
    if slug:
        return f"{base.rstrip('/')}/{slug}.html"[:500]
    return base.rstrip("/")


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
        sku = str(prod.get("sku") or "").strip()
        if not nombre or not sku:
            continue
        blob = f"{nombre} {sku} {prod.get('url_key') or ''}"
        seed_match = seed_match_for_med(blob, pais, med)
        if not coincide(blob, med) and not seed_match:
            continue
        precio_lista, precio_oferta = _precios(prod)
        precio = precio_lista or precio_oferta
        if not precio:
            continue
        n_lista = int(med["n"])
        clave = (sku, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [],
            "tipo_presentacion": nombre,
            "laboratorio": "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {pais} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        ficha = parse_ficha(nombre, med2)
        stock = str(prod.get("stock_status") or "").strip().upper().replace(" ", "_")
        if stock in ("IN_STOCK", "IN_STOCK_STATUS", "1", "TRUE"):
            disp = "Disponible"
        elif stock in ("OUT_OF_STOCK", "0", "FALSE"):
            disp = "Agotado"
        elif precio:
            # GraphQL a veces omite stock_status en productos vendibles
            disp = "Disponible"
        else:
            disp = "Consultar"
        out.append(
            {
                "pais": pais,
                "farmacia": farmacia,
                "fuente_url": url_pdp(base, prod),
                "id_producto_farmacia": sku[:80],
                "sku": sku[:80],
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
                "disponibilidad": disp,
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
                productos, fecha, err = buscar_magento(
                    s, alias, base=base, cache=cache, forzar=False if red_caida else forzar
                )
                if err and not red_caida:
                    if err.startswith("bloqueado") or "SSLError" in err:
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
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
        if not filas:
            print(" Sin filas: no se purgan vigentes (posible bloqueo o catálogo sin match).")
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
