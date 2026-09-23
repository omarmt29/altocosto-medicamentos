"""
Scraper PA · Farmacias Arrocha (Shopify) → P_aguila.medicamentos_altos_costos_america

La tienda online mezcla OTC/dermocosmética; especialidad de alto costo suele
estar poco cubierta. Se usa suggest.json + ficha /products/{handle}.json.

Uso:
    python scrapper/pa_arrocha.py
    python scrapper/pa_arrocha.py --fresh
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.matching import clasificar, coincide  # noqa: E402
from scrapper.report_seeds import seed_match_for_med  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.shopify_tienda import precios_variant  # noqa: E402
from scrapper.vtex_tienda import queries_es  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "arrocha"
BASE = "https://www.arrocha.com"
PAIS = "Panamá"
FARMACIA = "Arrocha"
# Precios Shopify publicados en USD; PAB está a la par (1:1).
MONEDA = "USD"

PAUSA = 0.35
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "es-PA,es;q=0.9,en;q=0.8",
            "Referer": BASE + "/",
            "Origin": BASE,
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def precio_variant(v: dict[str, Any]) -> float | None:
    """Precio de lista (compare_at) si hay descuento; si no, price."""
    lista, oferta = precios_variant(v)
    return lista or oferta


def enriquecer(s: requests.Session, handle: str) -> dict[str, Any] | None:
    """Ficha completa Shopify (precio/stock más fiables que suggest)."""
    if not handle:
        return None
    path = CACHE / f"p_{re.sub(r'[^a-z0-9]+', '_', handle.lower())[:80]}.json"
    if path.exists() and path.stat().st_size >= 2:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("product"):
                return data["product"]
        except Exception:
            pass
    time.sleep(PAUSA)
    try:
        r = s.get(f"{BASE}/products/{quote(handle)}.json", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200 or not (r.text or "").startswith("{"):
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    prod = data.get("product")
    if not isinstance(prod, dict):
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return prod


def buscar(s: requests.Session, alias: str, *, forzar: bool) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    time.sleep(PAUSA)
    url = (
        f"{BASE}/search/suggest.json?q={quote(alias)}"
        f"&resources[type]=product&resources[limit]=10"
        f"&resources[options][unavailable_products]=last"
    )
    try:
        r = s.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 451):
        return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code == 429:
        return [], datetime.now().date().isoformat(), "HTTP 429"
    if r.status_code != 200:
        return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    prods = ((data.get("resources") or {}).get("results") or {}).get("products") or []
    if not isinstance(prods, list):
        prods = []

    enriquecidos: list[dict[str, Any]] = []
    for p in prods:
        if not isinstance(p, dict):
            continue
        handle = str(p.get("handle") or "").strip()
        full = enriquecer(s, handle) if handle else None
        enriquecidos.append(full or p)

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(enriquecidos, ensure_ascii=False), encoding="utf-8")
    return enriquecidos, datetime.now().date().isoformat(), None


def filas_de_hits(
    med: dict[str, Any],
    hits: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in hits:
        nombre = str(h.get("title") or h.get("name") or "").strip()
        if not nombre:
            continue
        vendor = str(h.get("vendor") or "").strip()
        tags = h.get("tags") or []
        tag_txt = " ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
        blob = " ".join(x for x in (nombre, vendor, tag_txt, str(h.get("body_html") or "")) if x)
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue

        variants = h.get("variants") if isinstance(h.get("variants"), list) else []
        if variants:
            v0 = variants[0] if isinstance(variants[0], dict) else {}
            precio_lista, precio_oferta = precios_variant(v0)
            disponible = bool(v0.get("available", True))
            vid = str(v0.get("id") or h.get("id") or "")
        else:
            precio_lista, precio_oferta = precios_variant(h)
            disponible = bool(h.get("available", True))
            vid = str(h.get("id") or "")
        precio = precio_lista or precio_oferta
        if not precio or not vid:
            continue

        handle = str(h.get("handle") or "").strip()
        fuente = f"{BASE}/products/{handle}" if handle else BASE
        p_fake = {
            "nombre": nombre,
            "principios_activos": [vendor],
            "tipo_presentacion": nombre,
            "laboratorio": vendor,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        n_lista = int(med2["n"])
        clave = (vid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": fuente[:500],
                "id_producto_farmacia": vid[:80],
                "sku": str((variants[0].get("sku") if variants else None) or handle or vid)[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": (vendor or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
                "precio_lista": precio_lista or precio,
                "precio_oferta": precio_oferta,
                "moneda": MONEDA,
                "disponibilidad": "Disponible" if disponible else "Agotado",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        for alias in queries_es(med, PAIS):
            hits, fecha, err = buscar(s, alias, forzar=forzar)
            if err:
                print(f"  aviso {alias}: {err}")
                continue
            filas.extend(filas_de_hits(med, hits, fecha, vistos))
            if len(filas) > n_antes:
                break
        print(f"  ·  {len(filas) - n_antes:2d}  {med['nombre']}" if len(filas) > n_antes else f"      0  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" PA Arrocha → medicamentos_altos_costos_america")
    print("=" * 64)
    filas = recolectar(forzar=forzar)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    asegurar_tabla()
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    elif forzar:
        print("  aviso: 0 coincidencias — no se purgan filas existentes")
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"Panamá Arrocha: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
