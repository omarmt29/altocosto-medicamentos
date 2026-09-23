"""
Scraper BR · Pague Menos (VTEX) → P_aguila.medicamentos_altos_costos_america

Busca cada ítem DAMAC/FOMAC en la tienda, guarda todas las concentraciones
y presentaciones (SKU) que coincidan.

Uso:
    python scrapper/br_paguemenos.py
    python scrapper/br_paguemenos.py --fresh
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
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import clasificar, coincide  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.report_seeds import extra_terms_for_med, seed_match_for_med  # noqa: E402
from scrapper.busqueda_marcas import combinar_fases
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.vtex_tienda import precios_item  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "paguemenos"
BASE = "https://www.paguemenos.com.br"
PAIS = "Brasil"
FARMACIA = "Pague Menos"
MONEDA = "BRL"
PAUSA = 0.25
PAGE = 50
MAX_PAGINAS = 4
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,es;q=0.8,en;q=0.7",
            "Referer": BASE + "/",
        }
    )
    return s


def queries_br(med: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in list(med["aliases"]) + extra_terms_for_med(PAIS, med):
        alias = str(raw).strip()
        if len(alias) < 4:
            continue
        candidatos = [alias]
        low = alias.lower()
        if low.endswith(("mab", "nib", "mib", "lib")) and not low.endswith("e"):
            candidatos.append(alias + "e")
        if low.startswith("inmuno"):
            candidatos.append("imuno" + alias[6:])
        if low.startswith("interferon") and "interferona" not in low:
            candidatos.append(alias.replace("interferon", "interferona").replace("Interferon", "Interferona"))
        for q in candidatos:
            k = q.lower()
            if k not in seen:
                seen.add(k)
                out.append(q)
    return out


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def buscar_vtex(s: requests.Session, alias: str, *, forzar: bool) -> tuple[list[dict[str, Any]], str]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha
    productos: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for pagina in range(MAX_PAGINAS):
        inicio = pagina * PAGE
        fin = inicio + PAGE - 1
        url = (
            f"{BASE}/api/catalog_system/pub/products/search"
            f"?ft={quote(alias)}&_from={inicio}&_to={fin}"
        )
        time.sleep(PAUSA)
        r = None
        for intento in range(4):
            r = s.get(url, timeout=TIMEOUT)
            if r.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (intento + 1))
                continue
            break
        if r is None:
            break
        if r.status_code not in (200, 206):
            r.raise_for_status()
        lote = r.json()
        if not isinstance(lote, list) or not lote:
            break
        for prod in lote:
            pid = str(prod.get("productId") or "")
            if not pid or pid in vistos:
                continue
            vistos.add(pid)
            productos.append(prod)
        if len(lote) < PAGE:
            break
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(productos, ensure_ascii=False), encoding="utf-8")
    return productos, datetime.now().date().isoformat()


def url_pdp(prod: dict[str, Any]) -> str:
    link = str(prod.get("link") or "").strip()
    if link.startswith("http"):
        return link[:500]
    slug = str(prod.get("linkText") or "").strip()
    if slug:
        return f"{BASE}/{slug}/p"
    return BASE


def blob_prod(prod: dict[str, Any], item: dict[str, Any]) -> str:
    # Solo nombre/marca: la descripción de VTEX cita fármacos combinados (letrozol+Kisqali, etc.).
    return " ".join(
        str(x or "")
        for x in (
            prod.get("productName"),
            item.get("nameComplete") or item.get("name"),
            prod.get("brand"),
        )
    )


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        items = prod.get("items") or [prod]
        for item in items:
            nombre = str(
                item.get("nameComplete")
                or item.get("name")
                or prod.get("productName")
                or ""
            ).strip()
            if not nombre:
                continue
            blob = blob_prod(prod, item)
            seed_match = seed_match_for_med(f"{blob} {nombre}", PAIS, med)
            if not coincide(blob, med) and not coincide(nombre, med) and not seed_match:
                continue
            precio_lista, precio_oferta, qty = precios_item(item)
            precio = precio_lista or precio_oferta
            pid = str(item.get("itemId") or prod.get("productId") or "")
            if not pid:
                continue
            p_fake = {
                "nombre": nombre,
                "principios_activos": [prod.get("brand")],
                "tipo_presentacion": nombre,
                "laboratorio": prod.get("brand"),
            }
            med2, calidad, obs = clasificar(med, p_fake)
            if seed_match and calidad == "ok":
                calidad = "revisar"
            if seed_match:
                extra_obs = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
                obs = f"{obs} | {extra_obs}" if obs else extra_obs
            n_lista = int(med2["n"])
            clave = (pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(nombre, med2)
            lab = (prod.get("brand") or ficha.get("laboratorio") or "")[:200] or None
            ean = str(item.get("ean") or prod.get("productReference") or pid)[:80]
            out.append(
                {
                    "pais": PAIS,
                    "farmacia": FARMACIA,
                    "fuente_url": url_pdp(prod),
                    "id_producto_farmacia": pid[:80],
                    "sku": ean,
                    "n_lista": n_lista,
                    "medicamento_lista": str(med2["nombre"]),
                    "programa": str(med2["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": ficha.get("principio_activo"),
                    "concentracion": ficha.get("concentracion"),
                    "presentacion": ficha.get("presentacion"),
                    "laboratorio": lab,
                    "precio": precio,
                    "precio_lista": precio_lista or precio,
                    "precio_oferta": precio_oferta,
                    "moneda": MONEDA,
                    "disponibilidad": "Disponible" if qty > 0 and precio else "Agotado",
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def recolectar(forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        for fase, aliases in combinar_fases(PAIS, med, lambda _p, m: queries_br(m)):
            if fase == "marcas" and len(filas) > n_antes:
                break
            for alias in aliases:
                try:
                    productos, fecha = buscar_vtex(s, alias, forzar=forzar)
                except Exception as exc:
                    print(f"  error {med['nombre']!s} / {alias}: {exc}")
                    continue
                filas.extend(filas_de_productos(med, productos, fecha, vistos))
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_fomac = "--fomac" in sys.argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" BR Pague Menos → medicamentos_altos_costos_america")
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    print("=" * 64)
    filas = recolectar(forzar=forzar, meds=meds)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    revisar = len(filas) - ok
    con_precio = sum(1 for f in filas if f.get("precio"))
    print(f"Lista: {len(meds)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={revisar}, con precio={con_precio})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac:
        borrados = 0
    else:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · "
        f"obsoletos: {borrados} · "
        f"BR Pague Menos en tabla: {contar(PAIS, FARMACIA)} · "
        f"total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
