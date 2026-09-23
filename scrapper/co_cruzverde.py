"""
Scraper CO · Cruz Verde (api.cruzverde.com.co / Salesforce Commerce)

API observada (navegador):
  GET /product-service/products/detail/{productId}?inventoryId=COCV_zona64
  GET /product-service/products/search?q=...&page=&size=&inventoryId=COCV_zona64

Auth: cookie de sesión ``connect.sid`` (no Bearer).
  CRUZVERDE_COOKIE='connect.sid=s%3Acolombia-....'

IDs: prefijo COCV_ + SKU. Precios: price / prices['price-sale-col'].
Zona Bogotá por defecto: COCV_zona64 (query param ``inventoryId``).

Uso:
    export CRUZVERDE_COOKIE='connect.sid=...'
    python scrapper/co_cruzverde.py --fresh

En este datacenter el proxy corporativo bloquea api.cruzverde.com.co
aunque la cookie sea válida (Blocked site / Online Shopping).
"""

from __future__ import annotations

import json
import os
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
from scrapper.vtex_tienda import queries_es, fases_busqueda  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "cruzverde"
API = "https://api.cruzverde.com.co"
WEB = "https://www.cruzverde.com.co"
PAIS = "Colombia"
FARMACIA = "Cruz Verde"
MONEDA = "COP"
ZONA = os.environ.get("CRUZVERDE_ZONA", "COCV_zona64")
PAUSA = 0.3
TIMEOUT = 40
PAGE_SIZE = 40
MAX_PAGES = 3
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36 Edg/151.0.0.0"
)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Origin": WEB,
            "Referer": WEB + "/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
    )
    cookie = (os.environ.get("CRUZVERDE_COOKIE") or "").strip()
    if cookie:
        # Acepta cookie completa o solo el valor de connect.sid
        if "connect.sid=" not in cookie and cookie.startswith("s%3A"):
            cookie = f"connect.sid={cookie}"
        elif "connect.sid=" not in cookie and cookie.startswith("s:"):
            cookie = f"connect.sid={cookie}"
        s.headers["Cookie"] = cookie
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def _bloqueado(r: requests.Response) -> bool:
    if r.status_code in (401, 403, 451):
        return True
    if "block/webcat" in (r.url or ""):
        return True
    head = (r.text or "")[:300].lower()
    return "blocked site" in head or "access denied" in head


def precio_producto(p: dict[str, Any]) -> float | None:
    """Precio de lista; no usar sale/promo."""
    prices = p.get("prices") if isinstance(p.get("prices"), dict) else {}
    for key in ("price-list-col", "list", "price-sale-col", "sale"):
        raw = prices.get(key)
        try:
            v = float(raw)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    for key in ("listPrice", "price", "salePrice"):
        raw = p.get(key)
        try:
            v = float(raw)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    return None


def url_pdp(p: dict[str, Any]) -> str:
    pid = str(p.get("id") or "").strip()
    slug = str(p.get("pageUrl") or "").strip().strip("/")
    if slug:
        return f"{WEB}/{slug}.html"[:500] if not slug.endswith(".html") else f"{WEB}/{slug}"[:500]
    if pid:
        return f"{WEB}/pdp/{pid}.html"[:500]
    return WEB


def normalizar_hit(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    # search puede envolver en productData
    p = raw.get("productData") if isinstance(raw.get("productData"), dict) else raw
    if not isinstance(p, dict):
        return None
    pid = str(p.get("id") or raw.get("id") or "").strip()
    if not pid:
        return None
    if not pid.startswith("COCV_"):
        # a veces viene solo el número
        if pid.isdigit():
            pid = f"COCV_{pid}"
            p = {**p, "id": pid}
    return p


def buscar(s: requests.Session, alias: str, *, forzar: bool) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for page in range(MAX_PAGES):
        time.sleep(PAUSA)
        url = (
            f"{API}/product-service/products/search"
            f"?q={quote(alias)}&page={page}&size={PAGE_SIZE}&inventoryId={quote(ZONA)}"
        )
        try:
            r = s.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            return [], datetime.now().date().isoformat(), str(exc)
        if _bloqueado(r):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        if r.status_code != 200:
            return [], datetime.now().date().isoformat(), f"HTTP {r.status_code}"
        try:
            data = r.json()
        except ValueError:
            return [], datetime.now().date().isoformat(), "respuesta no JSON"

        hits: list[Any] = []
        if isinstance(data, list):
            hits = data
        elif isinstance(data, dict):
            for key in ("products", "content", "items", "hits", "results", "data"):
                val = data.get(key)
                if isinstance(val, list):
                    hits = val
                    break
                if isinstance(val, dict) and isinstance(val.get("products"), list):
                    hits = val["products"]
                    break
        if not hits:
            break
        for raw in hits:
            p = normalizar_hit(raw)
            if not p:
                continue
            pid = str(p["id"])
            if pid in vistos:
                continue
            vistos.add(pid)
            # enriquecer con detail si falta precio
            if precio_producto(p) is None:
                det = detalle(s, pid)
                if det:
                    p = {**p, **det}
            productos.append(p)
        if len(hits) < PAGE_SIZE:
            break

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def detalle(s: requests.Session, product_id: str) -> dict[str, Any] | None:
    time.sleep(PAUSA / 2)
    url = f"{API}/product-service/products/detail/{quote(product_id)}"
    try:
        r = s.get(url, timeout=TIMEOUT, params={"inventoryId": ZONA})
    except requests.RequestException:
        return None
    if r.status_code == 304:
        return None
    if r.status_code != 200 or _bloqueado(r):
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    return normalizar_hit(data)


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in productos:
        nombre = str(p.get("name") or "").strip()
        if not nombre:
            continue
        lab = str(p.get("laboratory") or p.get("brand") or p.get("subBrand") or "").strip()
        blob = " ".join(
            x
            for x in (
                nombre,
                lab,
                str(p.get("pageKeywords") or ""),
                str(p.get("pageDescription") or ""),
                str(p.get("notation") or ""),
            )
            if x
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue
        precio = precio_producto(p)
        if not precio:
            continue
        pid = str(p.get("id") or "")
        if not pid:
            continue
        p_fake = {
            "nombre": nombre,
            "principios_activos": [lab],
            "tipo_presentacion": nombre,
            "laboratorio": lab,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
            obs = f"{obs} | {extra}" if obs else extra
        n_lista = int(med2["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        stock = p.get("stock")
        stock_n: int | None
        if isinstance(stock, bool):
            stock_n = 1 if stock else 0
        elif stock is None or stock == "":
            stock_n = None
        else:
            try:
                stock_n = int(stock)
            except (TypeError, ValueError):
                stock_n = None
        if stock_n is None:
            disp = "Disponible" if precio else "Consultar"
        else:
            disp = "Disponible" if stock_n > 0 else "Agotado"
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": url_pdp(p),
                "id_producto_farmacia": pid[:80],
                "sku": pid.replace("COCV_", "")[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": (lab or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": disp,
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
    red_caida = False
    aviso = False
    for med in trabajo:
        n_antes = len(filas)
        for fase, aliases in fases_busqueda(PAIS, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                if red_caida:
                    path = cache_path(alias)
                    if not path.exists():
                        continue
                    productos, fecha, err = buscar(s, alias, forzar=False)
                else:
                    productos, fecha, err = buscar(s, alias, forzar=forzar)
                    if err:
                        if err.startswith("bloqueado") or "SSLError" in err:
                            red_caida = True
                            if not aviso:
                                print(f"  red no disponible ({err}). Sigo con caché local.")
                                print(
                                    "  Tip: exporta CRUZVERDE_COOKIE='connect.sid=...' "
                                    "(cookie del navegador) y corre fuera del proxy corporativo."
                                )
                                aviso = True
                        else:
                            print(f"  aviso {alias}: {err}")
                        continue
                filas.extend(filas_de_productos(med, productos, fecha, vistos))
        n_nuevas = len(filas) - n_antes
        print(f"  {'·' if n_nuevas else ' '} {n_nuevas:3d}  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_fomac = "--fomac" in sys.argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" CO Cruz Verde → medicamentos_altos_costos_america")
    print(f" API {API} · zona {ZONA}")
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    print("=" * 64)
    filas = recolectar(forzar=forzar, meds=meds)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
        if not filas and not solo_fomac:
            print("  aviso: 0 coincidencias — no se purgan filas existentes")
    else:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {FARMACIA}: {contar(PAIS, FARMACIA)} · total: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
