"""Scraper PY · Biggie (API app.biggie.com.py).

Flujo: autocomplete?query= → detalle /api/articles/{id} con precio.
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.matching import clasificar, coincide  # noqa: E402
from scrapper.precios import as_float, pares_lista_oferta  # noqa: E402
from scrapper.report_seeds import seed_match_for_med  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "biggie_py"
API = "https://api.app.biggie.com.py"
BASE = "https://biggie.com.py"
PAIS = "Paraguay"
FARMACIA = "Biggie"
MONEDA = "PYG"
PAUSA = 0.3
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "Origin": BASE,
            "Referer": BASE + "/",
        }
    )
    return s


def autocomplete(s: requests.Session, alias: str) -> list[dict[str, Any]]:
    try:
        r = s.get(
            API + "/api/articles/autocomplete",
            params={"query": alias},
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return []
    if r.status_code in (401, 403, 429, 503):
        return []
    if not r.ok:
        return []
    try:
        data = r.json()
    except ValueError:
        return []
    if isinstance(data, dict):
        items = data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return [x for x in items if isinstance(x, dict)]


def detalle(s: requests.Session, article_id: str) -> dict[str, Any] | None:
    try:
        r = s.get(f"{API}/api/articles/{article_id}", timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if not r.ok:
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def buscar(
    s: requests.Session, alias: str, *, forzar: bool
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None

    sugeridos = autocomplete(s, alias)
    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for sug in sugeridos[:12]:
        aid = str(sug.get("id") or "").strip()
        if not aid or aid in vistos:
            continue
        vistos.add(aid)
        time.sleep(PAUSA)
        prod = detalle(s, aid)
        if prod:
            # keep autocomplete text as fallback name
            if not prod.get("name") and sug.get("text"):
                prod["name"] = sug["text"]
            productos.append(prod)

    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat(), None


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        nombre = str(prod.get("name") or "").strip()
        pid = str(prod.get("id") or "").strip()
        if not nombre or not pid:
            continue
        lista = as_float(prod.get("price"))
        oferta = as_float(prod.get("priceSaleOffer"))
        lista, oferta = pares_lista_oferta(lista, oferta)
        if not lista:
            continue
        brand = str(prod.get("brand") or prod.get("manufacturer") or "")
        blob = " ".join(
            str(x or "")
            for x in [
                nombre,
                brand,
                prod.get("activeIngredient"),
                prod.get("presentation"),
                prod.get("description"),
                prod.get("code"),
            ]
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        n_lista = int(med["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [prod.get("activeIngredient"), nombre],
            "tipo_presentacion": prod.get("presentation") or nombre,
            "laboratorio": brand,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
            obs = f"{obs} | {extra}" if obs else extra
        ficha = parse_ficha(f"{nombre} {prod.get('activeIngredient') or ''}", med2)
        code = str(prod.get("code") or pid)
        url = f"{BASE}/products/{code}"
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": url[:500],
                "id_producto_farmacia": pid[:80],
                "sku": code[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo")
                or (str(prod.get("activeIngredient") or "")[:500] or None),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion")
                or (str(prod.get("presentation") or "")[:120] or None),
                "laboratorio": ficha.get("laboratorio") or (brand or None),
                "precio": lista,
                "precio_lista": lista,
                "precio_oferta": oferta,
                "moneda": MONEDA,
                "disponibilidad": "Disponible" if prod.get("enabled", True) else "Consultar",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_fomac = "--fomac" in sys.argv
    meds = (
        MEDICAMENTOS
        if not solo_fomac
        else [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    )
    print("=" * 64)
    print(" PY Biggie → medicamentos_altos_costos_america")
    print("=" * 64)
    s = session()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for med in meds:
        for _fase, aliases in fases_busqueda(PAIS, med):
            for alias in aliases:
                productos, fecha, err = buscar(s, alias, forzar=forzar)
                if err:
                    continue
                filas.extend(filas_de_productos(med, productos, fecha, vistos))
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
            PAIS, FARMACIA, [(f["id_producto_farmacia"], f["n_lista"]) for f in filas]
        )
    )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {FARMACIA}: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
