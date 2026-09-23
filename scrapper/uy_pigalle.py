"""
Scraper UY · Pigalle (Magento suggest) → P_aguila.medicamentos_altos_costos_america

GraphQL de Magento responde 500; se usa /search/ajax/suggest/ con precios
en data-price-amount del HTML embebido.

Uso:
    python scrapper/uy_pigalle.py
    python scrapper/uy_pigalle.py --fresh
    python scrapper/uy_pigalle.py --cache
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

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
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "pigalle"
BASE = "https://www.pigalle.com.uy"
PAIS = "Uruguay"
FARMACIA = "Pigalle"
MONEDA = "UYU"

PAUSA = 0.22
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
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "es-UY,es;q=0.9,en;q=0.7",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": BASE + "/",
            "Origin": BASE,
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def _precio_html(price_html: str) -> float | None:
    m = re.search(r'data-price-amount="([0-9.]+)"', price_html or "")
    if not m:
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", price_html or "")
    if not m:
        return None
    try:
        n = float(m.group(1))
    except ValueError:
        return None
    return n if n > 0 else None


def buscar(
    s: requests.Session, alias: str, *, forzar: bool
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    time.sleep(PAUSA)
    url = f"{BASE}/search/ajax/suggest/?q={quote(alias)}"
    try:
        r = s.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 451):
        return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code != 200:
        return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    if not isinstance(data, list):
        data = []

    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for it in data:
        if not isinstance(it, dict) or it.get("type") != "product":
            continue
        title = str(it.get("title") or "").strip()
        href = str(it.get("url") or "").strip()
        if not title or not href:
            continue
        full = urljoin(BASE + "/", href)
        if full in vistos:
            continue
        vistos.add(full)
        precio = _precio_html(str(it.get("price") or ""))
        sku = str(it.get("id") or it.get("product_id") or "")
        if not sku:
            sku = re.sub(r"[^a-z0-9]+", "-", title.lower())[:80]
        productos.append(
            {
                "title": title,
                "url": full,
                "price": precio,
                "sku": sku,
                "image": it.get("image"),
            }
        )

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def _query_permitida(med: dict[str, Any], query: str) -> bool:
    """Solo aliases de lista + guía de marcas (no términos cruzados ruidosos)."""
    from scrapper.matching import norm
    from marcas import aliases_de_marcas

    q = norm(query)
    if len(q) < 4:
        return False
    if q in {
        "verde",
        "azul",
        "rojo",
        "negro",
        "blanco",
        "crema",
        "forte",
        "plus",
        "total",
        "simple",
    }:
        return False
    allowed = {norm(a) for a in med.get("aliases") or [] if len(norm(a)) >= 4}
    allowed |= {norm(a) for a in aliases_de_marcas(int(med["n"]))}
    return q in allowed


def _query_en_nombre(query: str, nombre: str) -> bool:
    from scrapper.matching import norm

    q = norm(query)
    h = norm(nombre)
    if len(q) < 4 or not h:
        return False
    return bool(re.search(rf"(^| ){re.escape(q)}( |$)", h))


def filas_de_hits(
    med: dict[str, Any],
    hits: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    *,
    query: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in hits:
        nombre = str(h.get("title") or "").strip()
        if not nombre:
            continue
        blob = nombre
        seed_match = seed_match_for_med(blob, PAIS, med)
        query_match = (
            bool(query)
            and _query_permitida(med, query)
            and _query_en_nombre(query, nombre)
        )
        if not coincide(blob, med) and not seed_match and not query_match:
            continue
        precio = h.get("price")
        try:
            precio_f = float(precio) if precio is not None else None
        except (TypeError, ValueError):
            precio_f = None
        if not precio_f or precio_f <= 0:
            continue
        sku = str(h.get("sku") or "")[:80]
        if not sku:
            continue
        p_fake = {
            "nombre": nombre,
            "principios_activos": [],
            "tipo_presentacion": nombre,
            "laboratorio": "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and not coincide(blob, med) and calidad == "ok":
            calidad = "revisar"
        if query_match and not coincide(blob, med):
            if calidad == "ok":
                calidad = "revisar"
            extra = f"Match por término de búsqueda '{query}'"
            obs = f"{obs} | {extra}" if obs else extra
        n_lista = int(med2["n"])
        clave = (sku, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": str(h.get("url") or BASE)[:500],
                "id_producto_farmacia": sku,
                "sku": sku,
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio_f,
                "moneda": MONEDA,
                "disponibilidad": "Disponible",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(*, forzar: bool = False, solo_cache: bool = False) -> list[dict[str, Any]]:
    s = session()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    red_caida = solo_cache
    aviso_red = False
    for med in MEDICAMENTOS:
        n_antes = len(filas)
        for fase, aliases in fases_busqueda(PAIS, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                if red_caida:
                    path = cache_path(alias)
                    if not path.exists():
                        continue
                productos, fecha, err = buscar(s, alias, forzar=False if red_caida else forzar)
                if err and not red_caida:
                    if err.startswith("bloqueado") or "SSLError" in err:
                        red_caida = True
                        if not aviso_red:
                            print(f"  red no disponible ({err}). Sigo con caché local.")
                            aviso_red = True
                    else:
                        print(f"  aviso {alias}: {err}")
                    continue
                filas.extend(filas_de_hits(med, productos, fecha, vistos, query=alias))
        n_nuevas = len(filas) - n_antes
        print(f"  {'·' if n_nuevas else ' '} {n_nuevas:3d}  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_cache = "--cache" in sys.argv
    print("=" * 64)
    print(" UY Pigalle → medicamentos_altos_costos_america")
    if solo_cache:
        print(" Solo caché local (sin red)")
    print("=" * 64)
    filas = recolectar(forzar=forzar, solo_cache=solo_cache)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos(
            PAIS, FARMACIA, [(f["id_producto_farmacia"], f["n_lista"]) for f in filas]
        )
    else:
        print(" Sin filas: no se purgan vigentes.")
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {FARMACIA}: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
