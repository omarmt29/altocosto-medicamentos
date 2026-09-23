"""Scraper TT · TriniPharma (API pública)."""

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
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.matching import clasificar, coincide  # noqa: E402
from scrapper.report_seeds import seed_match_for_med  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "trinipharma_tt"
BASE = "https://www.trinipharma.com"
API = "https://api.trinipharma.com/api/trini/GetProducts"
PAIS = "Trinidad y Tobago"
FARMACIA = "TriniPharma"
MONEDA = "TTD"
PAUSA = 0.25
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def buscar(
    s: requests.Session, alias: str, *, forzar: bool
) -> tuple[list[dict[str, Any]], str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return data, fecha, None
    try:
        r = s.get(
            API,
            params={"MaxRecords": 30, "PageNo": 1, "UseForGN": 1, "SearchText": alias},
            timeout=TIMEOUT,
        )
        if r.status_code in (401, 403, 429, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    if not isinstance(data, list):
        data = []
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data, datetime.now().date().isoformat(), None


def filas_de_productos(
    med: dict[str, Any],
    productos: list[dict[str, Any]],
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for prod in productos:
        nombre = str(prod.get("ProductName") or "").strip()
        pid = str(prod.get("ProductNo") or "").strip()
        if not nombre or not pid:
            continue
        blob = " ".join(
            str(x or "")
            for x in (nombre, prod.get("Barcode"), prod.get("ProductTagsCSV"), pid)
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        try:
            precio = float(prod.get("SalesPrice") or 0)
        except (TypeError, ValueError):
            precio = 0.0
        if precio <= 0:
            continue
        n_lista = int(med["n"])
        clave = (pid, n_lista)
        if clave in vistos:
            continue
        vistos.add(clave)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [prod.get("ProductTagsCSV")],
            "tipo_presentacion": nombre,
            "laboratorio": "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        ficha = parse_ficha(nombre, med2)
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": f"{BASE}/productdetails/{quote(pid)}"[:500],
                "id_producto_farmacia": pid[:80],
                "sku": str(prod.get("Barcode") or pid)[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": "Agotado" if int(prod.get("IsSoldOut") or 0) else "Disponible",
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
    meds = MEDICAMENTOS if not solo_fomac else [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" TT TriniPharma → medicamentos_altos_costos_america")
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
    borrados = 0 if solo_fomac or not filas else purgar_obsoletos(PAIS, FARMACIA, [(f['id_producto_farmacia'], f['n_lista']) for f in filas])
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"{PAIS} {FARMACIA}: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
