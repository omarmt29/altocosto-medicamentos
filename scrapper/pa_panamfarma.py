"""
Scraper PA · Pan Am Farma → medicamentos_altos_costos_america

Farmacia de especialidad (oncológicos / biológicos) con PVP público en
WooCommerce Store API. Amplía cobertura en Panamá (Arrocha casi no trae alto costo).

Uso:
    python scrapper/pa_panamfarma.py
    python scrapper/pa_panamfarma.py --fresh
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
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import clasificar, medicamentos_que_pegan  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.precios import precios_woocommerce  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "panamfarma"
CATALOGO_CACHE = CACHE / "catalogo.json"
BASE = "https://panamfarma.com"
API = f"{BASE}/wp-json/wc/store/v1/products"
PAIS = "Panamá"
FARMACIA = "Pan Am Farma"
MONEDA = "USD"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PAUSA = 0.85
PER_PAGE = 100
MAX_PAGES = 25


def strip_html(s: Any) -> str:
    t = re.sub(r"<[^>]+>", " ", str(s or ""))
    return re.sub(r"\s+", " ", t).strip()


def precio_wc(p: dict[str, Any]) -> float | None:
    lista, oferta = precios_woocommerce(p)
    return lista or oferta


def bajar_catalogo(forzar: bool = False) -> list[dict[str, Any]]:
    if CATALOGO_CACHE.exists() and CATALOGO_CACHE.stat().st_size > 20 and not forzar:
        data = json.loads(CATALOGO_CACHE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            print(f"Catálogo Pan Am Farma en caché: {len(data)} productos")
            return data
    print(f"Descargando catálogo Pan Am Farma ({API}) …")
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})
    out: list[dict[str, Any]] = []
    for page in range(1, MAX_PAGES + 1):
        r = session.get(API, params={"per_page": PER_PAGE, "page": page}, timeout=50)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            print(f"  fin en página {page}")
            break
        out.extend(data)
        print(f"  página {page}: +{len(data)} (total {len(out)})")
        time.sleep(PAUSA)
    CACHE.mkdir(parents=True, exist_ok=True)
    CATALOGO_CACHE.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Catálogo vivo: {len(out)} productos")
    return out


def filas_para_db(catalogo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for p in catalogo:
        nombre = str(p.get("name") or "").strip()
        desc = strip_html(p.get("short_description") or p.get("description") or "")
        cats = " ".join(
            str(c.get("name") or "")
            for c in (p.get("categories") or [])
            if isinstance(c, dict)
        )
        url = str(p.get("permalink") or "")
        precio_lista, precio_oferta = precios_woocommerce(p)
        precio = precio_lista or precio_oferta
        if not nombre or not precio:
            continue
        texto = f"{nombre} {desc} {cats} {url}"
        hits = medicamentos_que_pegan(texto)
        if not hits:
            continue
        fake = {
            "nombre": nombre,
            "principios_activos": [desc, cats],
            "principios_activos_con_dosaje": [],
            "tipo_presentacion": desc or nombre,
        }
        for med0 in hits:
            med, calidad, obs = clasificar(med0, fake)
            n_lista = int(med["n"])
            pid = str(p.get("id") or "")
            clave = (pid, n_lista)
            if not pid or clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(f"{nombre} {desc}", med)
            raw_stock = p.get("is_in_stock")
            if raw_stock is None:
                disp = "Disponible"
            else:
                truthy = raw_stock in (True, 1, "1", "true", "True", "yes", "YES", "si", "Sí")
                disp = "Disponible" if truthy else "Agotado"
            out.append(
                {
                    "pais": PAIS,
                    "farmacia": FARMACIA,
                    "fuente_url": url[:500] if url else BASE,
                    "id_producto_farmacia": pid[:80],
                    "sku": str(p.get("sku") or pid)[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": ficha.get("principio_activo"),
                    "concentracion": ficha.get("concentracion") or None,
                    "presentacion": ficha.get("presentacion") or None,
                    "laboratorio": ficha.get("laboratorio"),
                    "precio": precio,
                    "precio_lista": precio_lista or precio,
                    "precio_oferta": precio_oferta,
                    "moneda": MONEDA,
                    "disponibilidad": disp,
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" PA Pan Am Farma → medicamentos_altos_costos_america")
    print("=" * 64)
    catalogo = bajar_catalogo(forzar=forzar)
    filas = filas_para_db(catalogo)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista DAMAC/FOMAC: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"PA Pan Am Farma: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
