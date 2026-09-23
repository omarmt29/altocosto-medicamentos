"""
Scraper PE · Boticas Perú (Demandware Search-UpdateGrid)
→ P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/pe_boticasperu.py
    python scrapper/pe_boticasperu.py --fresh
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

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

CACHE = ROOT / "cache" / "farmacias" / "boticasperu"
BASE = "https://www.boticasperu.pe"
PAIS = "Perú"
FARMACIA = "Boticas Perú"
MONEDA = "PEN"

PAUSA = 0.25
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

RE_VALUE = re.compile(r'content="(\d+(?:\.\d+)?)"')
RE_SOLES = re.compile(r"S/\s*([\d]+(?:\.\d+)?)")
RE_PID = re.compile(r'data-pid="([^"]+)"', flags=re.I)
RE_HREF = re.compile(r'<a href="([^"]+\.html)"', flags=re.I)
RE_TITLE = re.compile(r'(?:title|alt)="([^"]+)"', flags=re.I)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-PE,es;q=0.9",
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def precio_tile(chunk: str) -> float | None:
    """Precio base: si hay varios valores en el tile, tomar el mayor (lista)."""
    vals: list[float] = []
    for m in RE_VALUE.finditer(chunk):
        try:
            p = float(m.group(1))
        except ValueError:
            continue
        if p > 0:
            vals.append(p)
    for m in RE_SOLES.finditer(chunk):
        try:
            p = float(m.group(1))
        except ValueError:
            continue
        if p > 0:
            vals.append(p)
    return max(vals) if vals else None


def buscar(s: requests.Session, alias: str, *, forzar: bool) -> tuple[str, str, str | None]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        html = data.get("html") if isinstance(data, dict) else ""
        if html:
            fecha = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
            return str(html), fecha, None

    time.sleep(PAUSA)
    url = (
        f"{BASE}/on/demandware.store/Sites-BoticasPeru-Site/es_PE/"
        f"Search-UpdateGrid?q={quote(alias)}"
    )
    try:
        r = s.get(
            url,
            timeout=TIMEOUT,
            headers={"Referer": f"{BASE}/search?q={quote(alias)}", "Accept": "text/html"},
        )
    except requests.RequestException as exc:
        return "", datetime.now().date().isoformat(), str(exc)
    if r.status_code in (401, 403, 451):
        return "", datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
    if r.status_code != 200:
        return "", datetime.now().date().isoformat(), f"HTTP {r.status_code}"
    html = r.text or ""
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"html": html}, ensure_ascii=False), encoding="utf-8")
    return html, datetime.now().date().isoformat(), None


def filas_de_html(
    med: dict[str, Any],
    html: str,
    fecha_dato: str,
    vistos: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    tiles = re.split(r'class="product-tile"', html)
    for chunk in tiles[1:]:
        mtitle = RE_TITLE.search(chunk)
        if not mtitle:
            continue
        nombre = unescape(mtitle.group(1)).strip().rstrip(",")
        if not nombre:
            continue
        seed_match = seed_match_for_med(nombre, PAIS, med)
        if not coincide(nombre, med) and not seed_match:
            continue
        precio = precio_tile(chunk)
        if not precio:
            continue
        mpid = RE_PID.search(chunk)
        mhref = RE_HREF.search(chunk)
        href = mhref.group(1) if mhref else ""
        pid = (mpid.group(1) if mpid else "") or unquote(href).rstrip("/").split("/")[-1].replace(".html", "")
        pid = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(pid))[:80]
        if not pid:
            continue
        fuente = href if href.startswith("http") else (BASE + href if href else BASE)
        p_fake = {
            "nombre": nombre,
            "principios_activos": [],
            "tipo_presentacion": nombre,
            "laboratorio": "",
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
        agotado = "agotado" in chunk.lower() or "sin stock" in chunk.lower() or 'unavailable="true"' in chunk.lower()
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": fuente[:500],
                "id_producto_farmacia": pid,
                "sku": pid,
                "n_lista": n_lista,
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio"),
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": "Agotado" if agotado else "Disponible",
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
                html, fecha, err = buscar(s, alias, forzar=forzar)
                if err:
                    print(f"  aviso {alias}: {err}")
                    continue
                filas.extend(filas_de_html(med, html, fecha, vistos))
                if len(filas) > n_antes:
                    break
        print(f"  ·  {len(filas) - n_antes:2d}  {med['nombre']}" if len(filas) > n_antes else f"      0  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" PE Boticas Perú → medicamentos_altos_costos_america")
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
        f"Perú Boticas: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
