"""
Scraper UY · Farmacia Goes → P_aguila.medicamentos_altos_costos_america

Búsqueda HTML en /medicamentos?q=…; precio en itemprop=price del PDP.

Uso:
    python scrapper/uy_goes.py
    python scrapper/uy_goes.py --fresh
    python scrapper/uy_goes.py --cache
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
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "goes"
BASE = "https://www.farmaciagoes.com.uy"
PAIS = "Uruguay"
FARMACIA = "Farmacia Goes"
MONEDA = "UYU"

PAUSA = 0.3
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PROD_RE = re.compile(
    r'href="(https://www\.farmaciagoes\.com\.uy/medicamentos/([^"]+)_(\d+)_(\d+))"'
)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json",
            "Accept-Language": "es-UY,es;q=0.9",
            "Referer": BASE + "/",
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def slug_a_nombre(slug: str) -> str:
    base = re.sub(r"_\d+_\d+$", "", slug)
    return base.replace("-", " ").strip()


def enriquecer_precio(s: requests.Session, url: str, sku: str) -> float | None:
    path = CACHE / f"p_{sku}.json"
    if path.exists() and path.stat().st_size >= 2:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("price"):
                return float(data["price"])
        except Exception:
            pass
    time.sleep(PAUSA)
    try:
        r = s.get(url, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    m = re.search(r'itemprop="price"[^>]*content="([^"]+)"', r.text, re.I)
    if not m:
        m = re.search(r'content="([^"]+)"[^>]*itemprop="price"', r.text, re.I)
    if not m:
        return None
    try:
        precio = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    if precio <= 0:
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"price": precio, "url": url}, ensure_ascii=False), encoding="utf-8")
    return precio


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
    url = f"{BASE}/medicamentos?q={quote(alias)}"
    try:
        r = s.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 451):
        return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code != 200:
        return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"

    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for m in PROD_RE.finditer(r.text):
        href, slug, sku_a, sku_b = m.group(1), m.group(2), m.group(3), m.group(4)
        sku = sku_a or sku_b
        if not sku or sku in vistos:
            continue
        vistos.add(sku)
        nombre = slug_a_nombre(f"{slug}_{sku_a}_{sku_b}")
        precio = enriquecer_precio(s, href, sku)
        productos.append(
            {
                "id": sku,
                "title": nombre,
                "url": href,
                "price": precio,
            }
        )

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def _query_permitida(med: dict[str, Any], query: str) -> bool:
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
        seed_match = seed_match_for_med(nombre, PAIS, med)
        query_match = (
            bool(query)
            and _query_permitida(med, query)
            and _query_en_nombre(query, nombre)
        )
        if not coincide(nombre, med) and not seed_match and not query_match:
            continue
        precio = h.get("price")
        try:
            precio_f = float(precio) if precio is not None else None
        except (TypeError, ValueError):
            precio_f = None
        if not precio_f or precio_f <= 0:
            continue
        sku = str(h.get("id") or "")[:80]
        if not sku:
            continue
        p_fake = {
            "nombre": nombre,
            "principios_activos": [],
            "tipo_presentacion": nombre,
            "laboratorio": "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and not coincide(nombre, med) and calidad == "ok":
            calidad = "revisar"
        if query_match and not coincide(nombre, med):
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
    print(" UY Farmacia Goes → medicamentos_altos_costos_america")
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
