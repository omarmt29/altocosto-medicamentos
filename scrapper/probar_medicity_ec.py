"""
Prueba de cobertura EC en Farmacias Medicity (VTEX / farmaenlace).

Medicity expone API VTEX estándar, pero los biológicos/oncológicos de alto costo
no aparecen en el catálogo público online; el programa PMF/Especialidad opera fuera
del e-commerce indexable.

Uso:
    python scrapper/probar_medicity_ec.py
    python scrapper/probar_medicity_ec.py --json salida/medicity_probe_ec.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import coincide  # noqa: E402
from scrapper.vtex_tienda import queries_es  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://www.farmaciasmedicity.com"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PAUSA = 0.35


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-EC,es;q=0.9",
            "Referer": BASE + "/",
        }
    )
    return s


def buscar_catalog(s: requests.Session, term: str) -> tuple[list[dict[str, Any]], str | None]:
    url = (
        f"{BASE}/api/catalog_system/pub/products/search"
        f"?ft={quote(term)}&_from=0&_to=19"
    )
    try:
        r = s.get(url, timeout=40)
    except requests.RequestException as exc:
        return [], str(exc)
    if r.status_code in (401, 403, 451):
        return [], f"bloqueado HTTP {r.status_code}"
    if r.status_code != 200:
        return [], f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return [], "respuesta no JSON"
    return data if isinstance(data, list) else [], None


def buscar_inteligente(s: requests.Session, term: str) -> tuple[list[dict[str, Any]], str | None]:
    url = (
        f"{BASE}/api/intelligent-search/v1/product-search"
        f"?query={quote(term)}&count=10&page=1&locale=es-EC"
    )
    try:
        r = s.get(url, timeout=40)
    except requests.RequestException as exc:
        return [], str(exc)
    if r.status_code in (401, 403, 451):
        return [], f"bloqueado HTTP {r.status_code}"
    if r.status_code != 200:
        return [], f"HTTP {r.status_code}"
    try:
        data = r.json()
    except ValueError:
        return [], "respuesta no JSON"
    prods = data.get("products") if isinstance(data, dict) else None
    return prods if isinstance(prods, list) else [], None


def nombres_productos(prods: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for prod in prods:
        for item in prod.get("items") or [prod]:
            nombre = str(
                item.get("nameComplete")
                or item.get("name")
                or prod.get("productName")
                or ""
            ).strip()
            if nombre:
                out.append(nombre)
    return out


def match_med(prods: list[dict[str, Any]], med: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for prod in prods:
        for item in prod.get("items") or [prod]:
            nombre = str(
                item.get("nameComplete")
                or item.get("name")
                or prod.get("productName")
                or ""
            )
            blob = " ".join(
                [
                    nombre,
                    str(prod.get("brand") or ""),
                    str(prod.get("description") or "")[:300],
                ]
            )
            if coincide(blob, med) or coincide(nombre, med):
                hits.append(nombre[:120])
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Prueba cobertura Medicity EC")
    ap.add_argument("--json", default="", help="Ruta para guardar informe JSON")
    args = ap.parse_args()

    s = session()
    bloqueo: str | None = None
    por_med: dict[str, Any] = {}
    encontrados = 0

    print(f"Probando {len(MEDICAMENTOS)} medicamentos en {BASE} …\n")

    for med in MEDICAMENTOS:
        nombre = str(med["nombre"])
        aliases = queries_es(med, "Ecuador")[:4]
        hits: list[str] = []
        err: str | None = None
        for alias in aliases:
            prods, err_cat = buscar_catalog(s, alias)
            time.sleep(PAUSA)
            if err_cat and not bloqueo:
                bloqueo = err_cat
            hits.extend(match_med(prods, med))
            if hits:
                break
            prods2, err_is = buscar_inteligente(s, alias)
            time.sleep(PAUSA)
            if err_is and not bloqueo:
                bloqueo = err_is
            hits.extend(match_med(prods2, med))
            if hits:
                break
        if hits:
            encontrados += 1
            print(f"  ✓ {nombre}: {hits[0]}")
        por_med[nombre] = {"aliases": aliases, "hits": hits, "error": err}
        if not hits and err:
            por_med[nombre]["ultimo_error"] = err

    print(f"\nResumen: {encontrados}/{len(MEDICAMENTOS)} con match")
    if bloqueo:
        print(f"Advertencia de red/bloqueo: {bloqueo}")

    # Categoría Medicina/Especialidad (id 532)
    cat_url = f"{BASE}/api/catalog_system/pub/products/search?fq=C:/522/532/&_from=0&_to=49"
    cat_err: str | None = None
    cat_nombres: list[str] = []
    try:
        r = s.get(cat_url, timeout=40)
        if r.status_code == 200:
            lote = r.json()
            if isinstance(lote, list):
                cat_nombres = nombres_productos(lote)
        else:
            cat_err = f"HTTP {r.status_code}"
    except requests.RequestException as exc:
        cat_err = str(exc)

    informe = {
        "fuente": BASE,
        "plataforma": "VTEX (cuenta farmaenlace)",
        "medicamentos_con_match": encontrados,
        "medicamentos_total": len(MEDICAMENTOS),
        "bloqueo_red": bloqueo,
        "categoria_especialidad_online": cat_nombres,
        "categoria_especialidad_error": cat_err,
        "detalle": por_med,
    }

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Informe guardado en {out}")

    return 0 if encontrados else 1


if __name__ == "__main__":
    raise SystemExit(main())
