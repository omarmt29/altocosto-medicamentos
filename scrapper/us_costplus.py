"""
Scraper US · Mark Cuban Cost Plus Drugs (Pricing API).

API: https://api.costplusdrugs.com/pricelist/cpd
Docs: https://mccpdc-llc.github.io/pricing-api-documentation/cpd.html
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "costplus_us"
API = "https://api.costplusdrugs.com/pricelist/cpd"
PAIS = "Estados Unidos"
FARMACIA = "Cost Plus Drugs"
MONEDA = "USD"
PAUSA = 0.1
TIMEOUT = 90
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


def catalogo(s: requests.Session, *, forzar: bool) -> list[dict[str, Any]]:
    path = CACHE / "_catalog.json"
    if not forzar and path.exists() and path.stat().st_size > 1000:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data
    time.sleep(PAUSA)
    r = s.get(API, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        data = []
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def precio_canal(row: dict[str, Any]) -> tuple[float | None, float | None, bool]:
    """Devuelve (precio, precio_lista, en_stock).

    Precio = total al paciente sin envío (pack + dispensing fee).
    Precio lista = solo medicamento (sample_pack_price).
    """
    ch = row.get("cpd_channel")
    if not isinstance(ch, dict):
        return None, None, False
    lista = parse_money(ch.get("sample_pack_price"))
    total = parse_money(ch.get("sample_pack_price_total_to_patient_without_shipping"))
    if not total:
        total = lista
    if not lista and total:
        lista = total
    en_stock = bool(ch.get("in_stock", True))
    return total, lista, en_stock


def blob_producto(row: dict[str, Any]) -> str:
    parts = [
        row.get("medication_name"),
        row.get("brand_name"),
        row.get("brand_generic"),
        row.get("strength"),
        row.get("form"),
        row.get("url"),
    ]
    return " ".join(str(p) for p in parts if p)


def filas_de_catalogo(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
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
        sku = str(row.get("external_sku") or "").strip()
        if not sku:
            ndcs = row.get("equivalent_ndcs") or []
            sku = str(ndcs[0]) if ndcs else ""
        if not sku:
            continue
        precio, precio_lista, en_stock = precio_canal(row)
        if not precio:
            continue
        n_lista = int(med["n"])
        clave = (sku, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        pack = row.get("sample_volume") or row.get("sample_pack_size") or row.get("pack_size")
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
            "tipo_presentacion": str(pack or row.get("form") or ""),
            "laboratorio": brand,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        ficha = parse_ficha(nombre, med2)
        fuente = str(row.get("url") or "").strip() or "https://www.costplusdrugs.com/"
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": fuente[:500],
                "id_producto_farmacia": sku[:80],
                "sku": sku[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo")
                or str(row.get("medication_name") or "")[:200],
                "concentracion": ficha.get("concentracion")
                or str(row.get("strength") or "")[:80]
                or None,
                "presentacion": ficha.get("presentacion") or str(pack or "")[:120] or None,
                "laboratorio": (brand or ficha.get("laboratorio") or "")[:200] or None,
                "precio": precio,
                "precio_lista": precio_lista or precio,
                "precio_oferta": None,
                "moneda": MONEDA,
                "disponibilidad": "Disponible" if en_stock else "Agotado",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    print("  bajando pricelist Cost Plus Drugs…")
    productos = catalogo(s, forzar=forzar)
    print(f"  catálogo: {len(productos)} presentaciones")
    fecha = datetime.now().date().isoformat()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        filas.extend(filas_de_catalogo(med, productos, fecha, vistos))
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
