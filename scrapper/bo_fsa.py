"""Scraper BO · FSA Tienda Online (API pública de búsqueda)."""

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
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.matching import clasificar, coincide  # noqa: E402
from scrapper.report_seeds import seed_match_for_med  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402
from scrapper.vtex_tienda import fases_busqueda  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "fsa_bo"
BASE = "https://fsa.bo"
API = f"{BASE}/api/cargarProductosBusquedaOrden"
PAIS = "Bolivia"
FARMACIA = "FSA Tienda Online"
MONEDA = "BOB"
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
    s.headers.update({"User-Agent": UA, "Accept": "application/json, text/plain, */*"})
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
        r = s.post(
            API,
            data={
                "skip": 0,
                "limit": 32,
                "busqueda": alias,
                "orden": "ASC",
                "buscar": "nombreProducto",
            },
            timeout=TIMEOUT,
        )
        if r.status_code in (401, 403, 429, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        r.raise_for_status()
        payload = r.json()
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    except ValueError:
        return [], datetime.now().date().isoformat(), "respuesta no JSON"
    productos = payload.get("productos") if isinstance(payload, dict) else []
    if not isinstance(productos, list):
        productos = []
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
        raw = prod.get("_id") or {}
        nombre = str(raw.get("nombreProducto") or "").strip()
        pid = str(raw.get("idProducto") or "").strip()
        if not nombre or not pid:
            continue
        blob = " ".join(
            str(x or "")
            for x in [nombre, raw.get("descripcion"), raw.get("nombreLaboratorio"), raw.get("nombreCategoria")]
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        frac = float(raw.get("frac") or 1)
        try:
            precio = float(raw.get("precio") or 0) / (frac if frac > 0 else 1)
        except (TypeError, ValueError, ZeroDivisionError):
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
            "principios_activos": [raw.get("descripcion"), raw.get("nombreLaboratorio")],
            "tipo_presentacion": nombre,
            "laboratorio": raw.get("nombreLaboratorio") or "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        ficha = parse_ficha(f"{nombre} {raw.get('descripcion') or ''}", med2)
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": f"{BASE}/producto/detalle/{pid}"[:500],
                "id_producto_farmacia": pid[:80],
                "sku": str(raw.get("codigo") or pid)[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio") or (raw.get("nombreLaboratorio") or None),
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


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_fomac = "--fomac" in sys.argv
    meds = MEDICAMENTOS if not solo_fomac else [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" BO FSA Tienda Online → medicamentos_altos_costos_america")
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
