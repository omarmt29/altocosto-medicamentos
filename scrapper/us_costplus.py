"""
Scraper US · Mark Cuban Cost Plus Drugs (API pública).

API: https://us-central1-costplusdrugs-publicapi.cloudfunctions.net/main
Docs: https://costplusdrugs.github.io/apidocs/

Sin WAF/proxy problemático: catálogo JSON abierto + cotización por cantidad.
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
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "costplus_us"
API = "https://us-central1-costplusdrugs-publicapi.cloudfunctions.net/main"
PAIS = "Estados Unidos"
FARMACIA = "Cost Plus Drugs"
MONEDA = "USD"
PAUSA = 0.15
TIMEOUT = 60
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = True
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def parse_money(raw: Any) -> float | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    s = re.sub(r"[^0-9.]", "", s)
    if not s:
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return n if n > 0 else None


def pack_units(row: dict[str, Any]) -> int:
    """Unidades cotizables.

    Para comprimidos ``medispan_pack_size`` suele ser 30/90.
    Para inyectables a menudo viene en mL (0.4, 0.8) → cotizar 1 presentación.
    """
    form = str(row.get("form") or "").lower()
    pill = str(row.get("pill_nonpill") or "").lower() == "pill"
    raw = row.get("medispan_pack_size")
    try:
        n = float(str(raw))
    except (TypeError, ValueError):
        n = 0.0
    if pill and n >= 1:
        return int(n)
    # jeringas / kits / cajas: 1 presentación
    if any(x in form for x in ("syringe", "injector", "pen", "kit", "box", "vial", "solution")):
        return 1
    if 0 < n < 1:
        return 1
    if n >= 1:
        return int(n)
    return 1 if not pill else 30


def precio_fila(s: requests.Session, row: dict[str, Any]) -> tuple[float | None, int]:
    units = pack_units(row)
    q = cotizar(s, row, units)
    if q:
        return q, units
    unit = parse_money(row.get("unit_price"))
    if unit and units == 1:
        return unit, 1
    if unit and units > 1:
        return round(unit * units, 2), units
    return None, units


def catalogo(s: requests.Session, *, forzar: bool) -> list[dict[str, Any]]:
    path = CACHE / "_catalog.json"
    if not forzar and path.exists() and path.stat().st_size > 1000:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data
    time.sleep(PAUSA)
    r = s.get(API, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json().get("results") or []
    if not isinstance(data, list):
        data = []
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def cotizar(s: requests.Session, row: dict[str, Any], units: int) -> float | None:
    """Precio total para `units` unidades (pack típico)."""
    ndc = str(row.get("ndc") or "").strip()
    params: dict[str, Any] = {"quantity_units": units}
    if ndc:
        params["ndc"] = ndc
    else:
        params["medication_name"] = row.get("medication_name") or ""
        if row.get("strength"):
            params["strength"] = row["strength"]
    path = CACHE / f"q_{ndc or 'x'}_{units}.json"
    if path.exists() and path.stat().st_size > 2:
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            q = parse_money(cached.get("requested_quote"))
            if q:
                return q
        except Exception:
            pass
    time.sleep(PAUSA)
    try:
        r = s.get(API, params=params, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        results = r.json().get("results") or []
    except Exception:
        return None
    if not results:
        return None
    hit = results[0]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hit, ensure_ascii=False), encoding="utf-8")
    q = parse_money(hit.get("requested_quote"))
    if q:
        return q
    unit = parse_money(hit.get("unit_price") or row.get("unit_price"))
    return round(unit * units, 2) if unit else None


def blob_producto(row: dict[str, Any]) -> str:
    parts = [
        row.get("medication_name"),
        row.get("brand_name"),
        row.get("brand_generic"),
        row.get("strength"),
        row.get("form"),
        row.get("slug"),
    ]
    return " ".join(str(p) for p in parts if p)


def filas_de_catalogo(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
    s: requests.Session,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in productos:
        if not isinstance(row, dict):
            continue
        blob = blob_producto(row)
        if not blob:
            continue
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        ndc = str(row.get("ndc") or row.get("slug") or "").strip()
        if not ndc:
            continue
        n_lista = int(med["n"])
        clave = (ndc, n_lista)
        if clave in vistos:
            continue
        units = pack_units(row)
        precio, units = precio_fila(s, row)
        if not precio:
            continue
        vistos.add(clave)
        nombre = " ".join(
            x
            for x in (
                str(row.get("medication_name") or "").strip(),
                str(row.get("strength") or "").strip(),
                str(row.get("form") or "").strip(),
            )
            if x
        )
        brand = str(row.get("brand_name") or "").strip()
        if brand:
            nombre = f"{nombre} ({brand})" if nombre else brand
        p_fake = {
            "nombre": nombre,
            "principios_activos": [row.get("medication_name"), brand],
            "tipo_presentacion": f"{row.get('form') or ''} x {units}",
            "laboratorio": brand,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        ficha = parse_ficha(nombre, med2)
        fuente = str(row.get("url") or "").strip() or f"https://www.costplusdrugs.com/medications/{row.get('slug') or ''}/"
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": fuente[:500],
                "id_producto_farmacia": ndc[:80],
                "sku": ndc[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo") or str(row.get("medication_name") or "")[:200],
                "concentracion": ficha.get("concentracion") or str(row.get("strength") or "")[:80] or None,
                "presentacion": ficha.get("presentacion")
                or f"{row.get('form') or 'unit'} x {units}".strip()[:120],
                "laboratorio": (brand or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": "Disponible",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    print("  bajando catálogo Cost Plus Drugs…")
    productos = catalogo(s, forzar=forzar)
    print(f"  catálogo: {len(productos)} presentaciones")
    fecha = datetime.now().date().isoformat()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        # Primero match sobre catálogo completo (barato); fases solo para seeds extras.
        filas.extend(filas_de_catalogo(med, productos, fecha, vistos, s))
        if len(filas) == n_antes:
            for _fase, aliases in fases_busqueda(PAIS, med):
                for alias in aliases[:3]:
                    time.sleep(PAUSA)
                    try:
                        r = s.get(API, params={"medication_name": alias, "quantity_units": 30}, timeout=TIMEOUT)
                        extra = r.json().get("results") or [] if r.status_code == 200 else []
                    except Exception:
                        extra = []
                    if extra:
                        filas.extend(filas_de_catalogo(med, extra, fecha, vistos, s))
                        if len(filas) > n_antes:
                            break
                if len(filas) > n_antes:
                    break
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
    print(" US Cost Plus Drugs → medicamentos_altos_costos_america")
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    print("=" * 64)
    filas = recolectar(forzar=forzar, meds=meds)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista: {len(meds)} medicamentos")
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
    else:
        print("  aviso: 0 coincidencias — no se purgan filas existentes")
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {FARMACIA}: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
