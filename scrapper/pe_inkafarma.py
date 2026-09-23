"""
Scraper PE · Inkafarma (Algolia) → P_aguila.medicamentos_altos_costos_america

La web inkafarma.pe puede estar bloqueada por proxy; Algolia suele responder.

Uso:
    python scrapper/pe_inkafarma.py
    python scrapper/pe_inkafarma.py --fresh
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

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

CACHE = ROOT / "cache" / "farmacias" / "inkafarma"
BASE = "https://inkafarma.pe"
PAIS = "Perú"
FARMACIA = "Inkafarma"
MONEDA = "PEN"

ALGOLIA_APP = "15W622LAQ4"
ALGOLIA_KEY = "eb3261874e9b933efab019b04acff834"
ALGOLIA_INDEX = "products"
ALGOLIA_URL = f"https://{ALGOLIA_APP.lower()}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

PAUSA = 0.2
TIMEOUT = 40
HITS_POR_PAGINA = 40
MAX_PAGINAS = 3
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
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Algolia-Application-Id": ALGOLIA_APP,
            "X-Algolia-API-Key": ALGOLIA_KEY,
            "Origin": BASE,
            "Referer": BASE + "/",
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def precio_hit(h: dict[str, Any]) -> float | None:
    """Precio de lista (priceList); no usar promo/tarjeta."""
    for key in ("priceList", "validPrice", "priceWithCard", "pricePromo"):
        try:
            p = float(h.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if p > 0:
            return p
    return None


def url_pdp(h: dict[str, Any]) -> str:
    """PDP Inkafarma: /producto/{uri}/{objectID}."""
    uri = str(h.get("uri") or "").strip().strip("/")
    oid = str(h.get("objectID") or "").strip()
    if uri and oid:
        return f"{BASE}/producto/{uri}/{oid}"[:500]
    if uri:
        return f"{BASE}/producto/{uri}"[:500]
    if oid:
        # Sin slug: buscador por id (mejor que Algolia crudo).
        return f"{BASE}/buscador?keyword={oid}"[:500]
    return BASE


def buscar(s: requests.Session, alias: str, *, forzar: bool) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for page in range(MAX_PAGINAS):
        time.sleep(PAUSA)
        body = {"query": alias, "hitsPerPage": HITS_POR_PAGINA, "page": page}
        try:
            r = s.post(ALGOLIA_URL, json=body, timeout=TIMEOUT)
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
        if data.get("message"):
            return [], datetime.now().date().isoformat(), str(data["message"])
        hits = data.get("hits") or []
        if not isinstance(hits, list) or not hits:
            break
        for h in hits:
            if not isinstance(h, dict):
                continue
            pid = str(h.get("objectID") or h.get("skuSap") or "")
            if not pid or pid in vistos:
                continue
            vistos.add(pid)
            productos.append(h)
        nb_pages = int(data.get("nbPages") or 0)
        if page + 1 >= nb_pages:
            break

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def filas_de_hits(
    med: dict[str, Any],
    hits: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for h in hits:
        nombre = str(h.get("name") or "").strip()
        if not nombre:
            continue
        lab = str(h.get("laboratory") or h.get("lab") or h.get("brand") or "").strip()
        blob = " ".join(
            str(h.get(k) or "")
            for k in (
                "name",
                "composition",
                "keyword",
                "brand",
                "laboratory",
                "lab",
                "activePrinciples",
                "presentation",
            )
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
            continue
        precio = precio_hit(h)
        if not precio:
            continue
        pid = str(h.get("objectID") or h.get("skuSap") or "")
        if not pid:
            continue
        p_fake = {
            "nombre": nombre,
            "principios_activos": [lab],
            "tipo_presentacion": str(h.get("presentation") or nombre),
            "laboratorio": lab,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        n_lista = int(med2["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        ficha = parse_ficha(nombre, med2)
        stock = h.get("stock")
        try:
            stock_n = int(stock) if stock is not None else None
        except (TypeError, ValueError):
            stock_n = None
        if stock_n is None:
            disponible = True
        else:
            disponible = stock_n > 0
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": url_pdp(h),
                "id_producto_farmacia": pid[:80],
                "sku": str(h.get("skuSap") or pid)[:80],
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion") or str(h.get("presentation") or "")[:120] or None,
                "laboratorio": (lab or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
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
        for fase, aliases in fases_busqueda(PAIS, med):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
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
    print(" PE Inkafarma → medicamentos_altos_costos_america")
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
        f"Perú Inkafarma: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
