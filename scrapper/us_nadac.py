"""
Scraper US · NADAC (CMS / Medicaid.gov open data).

Fuente: National Average Drug Acquisition Cost — costo de adquisición promedio
nacional (no precio retail al paciente). Dataset DKAN 2026.

API: https://data.medicaid.gov/api/1/datastore/query/<dataset>/0
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
from scrapper.matching import clasificar, coincide, norm  # noqa: E402
from scrapper.report_seeds import seed_match_for_med  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "nadac_us"
# NADAC National Average Drug Acquisition Cost — Current Year (2026)
DATASET = "fbb83258-11c7-47f5-8b18-5f8e79f7e704"
API = f"https://data.medicaid.gov/api/1/datastore/query/{DATASET}/0"
PAIS = "Estados Unidos"
FARMACIA = "NADAC (CMS)"
MONEDA = "USD"
PAUSA = 0.12
TIMEOUT = 60
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = True
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )
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
    """Convierte NADAC por unidad a un pack comparable (≈30 tabs / 1 device)."""
    desc = str(row.get("ndc_description") or "").upper()
    unit = str(row.get("pricing_unit") or "").upper()
    if any(x in desc for x in ("AUTOINJECTOR", "AUTO-INJECTOR", "PEN", "SYRINGE", "KIT", "VIAL", "CARTRIDGE")):
        if unit == "ML":
            m = re.search(r"(\d+(?:\.\d+)?)\s*ML", desc)
            if m:
                vol = float(m.group(1))
                if 0 < vol <= 50:
                    return max(1, int(round(vol))) if vol >= 1 else 1
        return 1
    if unit == "ML":
        m = re.search(r"(\d+(?:\.\d+)?)\s*ML", desc)
        if m:
            vol = float(m.group(1))
            if vol >= 1:
                return int(round(vol))
        return 1
    if any(x in desc for x in (" TAB", "TABLET", " CAP", "CAPSULE", "SOFTGEL")):
        return 30
    if unit == "EA":
        return 30 if any(x in desc for x in ("TAB", "CAP")) else 1
    return 1


def terminos_busqueda(med: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for _fase, aliases in fases_busqueda(PAIS, med):
        for a in aliases:
            t = re.sub(r"[^A-Za-z0-9 /\-]+", " ", str(a)).strip()
            key = norm(t)
            if len(key) < 5 or key in seen:
                continue
            # Preferir INN/marca en ASCII (NADAC está en inglés)
            if re.search(r"[áéíóúñü]", t, re.I):
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= 6:
                return out
    return out


def consultar(s: requests.Session, termino: str, *, forzar: bool) -> list[dict[str, Any]]:
    safe = re.sub(r"[^a-z0-9]+", "_", termino.lower())[:60] or "q"
    path = CACHE / f"{safe}.json"
    if not forzar and path.exists() and path.stat().st_size > 20:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    time.sleep(PAUSA)
    payload = {
        "limit": 80,
        "conditions": [
            {"property": "ndc_description", "operator": "like", "value": f"%{termino}%"}
        ],
        "sorts": [{"property": "as_of_date", "order": "desc"}],
    }
    try:
        r = s.post(API, json=payload, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        data = r.json().get("results") or []
    except Exception:
        return []
    if not isinstance(data, list):
        data = []
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def filas_de_resultados(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Un NDC por descripción: quedarse con el más reciente / más barato
    best: dict[str, dict[str, Any]] = {}
    for row in productos:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("ndc_description") or "").strip()
        ndc = str(row.get("ndc") or "").strip()
        unit = parse_money(row.get("nadac_per_unit"))
        if not desc or not ndc or not unit:
            continue
        blob = desc
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        prev = best.get(ndc)
        if prev:
            if str(row.get("as_of_date") or "") < str(prev.get("as_of_date") or ""):
                continue
            if str(row.get("as_of_date") or "") == str(prev.get("as_of_date") or ""):
                if unit >= float(prev.get("_unit") or 0):
                    continue
        row = dict(row)
        row["_unit"] = unit
        row["_seed"] = seed_match
        best[ndc] = row

    for row in best.values():
        ndc = str(row.get("ndc") or "").strip()
        n_lista = int(med["n"])
        clave = (ndc, n_lista)
        if clave in vistos:
            continue
        unit = float(row["_unit"])
        units = pack_units(row)
        precio = round(unit * units, 2)
        if precio <= 0:
            continue
        vistos.add(clave)
        nombre = str(row.get("ndc_description") or "").strip()
        p_fake = {
            "nombre": nombre,
            "principios_activos": [nombre],
            "tipo_presentacion": f"{row.get('pricing_unit') or 'unit'} x {units}",
            "laboratorio": None,
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if row.get("_seed") and calidad == "ok":
            calidad = "revisar"
        note = "NADAC=costo adquisición (no retail)"
        obs = f"{obs}; {note}" if obs else note
        ficha = parse_ficha(nombre, med2)
        fuente = (
            "https://data.medicaid.gov/dataset/fbb83258-11c7-47f5-8b18-5f8e79f7e704"
        )
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
                "principio_activo": ficha.get("principio_activo") or str(med2["nombre"])[:200],
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion")
                or f"NADAC {row.get('pricing_unit') or 'unit'} × {units}"[:120],
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": "Referencia",
                "calidad": calidad,
                "observacion": obs,
                "fecha_publicacion": str(row.get("effective_date") or "")[:10] or None,
                "fecha_dato": fecha_dato,
            }
        )
    return out


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    fecha = datetime.now().date().isoformat()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    trabajo = meds if meds is not None else MEDICAMENTOS
    for med in trabajo:
        n_antes = len(filas)
        bag: list[dict[str, Any]] = []
        seen_ndc: set[str] = set()
        for term in terminos_busqueda(med):
            for row in consultar(s, term, forzar=forzar):
                ndc = str(row.get("ndc") or "")
                if not ndc or ndc in seen_ndc:
                    continue
                seen_ndc.add(ndc)
                bag.append(row)
            if len(bag) >= 40:
                break
        filas.extend(filas_de_resultados(med, bag, fecha, vistos))
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
    print(" US NADAC (CMS) → medicamentos_altos_costos_america")
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
