"""
Scraper CL · Farmacias Ahumada (Demandware Search-UpdateGrid)
→ P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/cl_ahumada.py
    python scrapper/cl_ahumada.py --fresh
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
from urllib.parse import quote

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
from scrapper.vtex_tienda import queries_es  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE = ROOT / "cache" / "farmacias" / "ahumada"
BASE = "https://www.farmaciasahumada.cl"
PAIS = "Chile"
FARMACIA = "Farmacias Ahumada"
MONEDA = "CLP"

PAUSA = 0.25
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

RE_PDP = re.compile(
    r'<div class="pdp-link">\s*<a class="link" href="(?P<href>[^"]+)">(?P<name>[^<]+)</a>',
    flags=re.I,
)
RE_PRICE_DOLLAR = re.compile(r"\$\s*([\d.]+)")
RE_VALUE = re.compile(r'class="value" content="(\d+(?:\.\d+)?)"')
RE_PID = re.compile(r'data-pid="(\d+)"', flags=re.I)
RE_UNAVAIL = re.compile(r'data-is-unavailable="true"', flags=re.I)


def session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CL,es;q=0.9",
        }
    )
    return s


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def clp(raw: str) -> float | None:
    """CLP en tienda: $760.199 → 760199 (punto = miles)."""
    s = re.sub(r"[^\d]", "", str(raw or ""))
    if not s:
        return None
    try:
        p = float(s)
    except ValueError:
        return None
    return p if p > 0 else None


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
        f"{BASE}/on/demandware.store/Sites-ahumada-cl-Site/default/"
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
    for m in RE_PDP.finditer(html):
        nombre = unescape(m.group("name")).strip()
        if not nombre:
            continue
        seed_match = seed_match_for_med(nombre, PAIS, med)
        if not coincide(nombre, med) and not seed_match:
            continue
        after = html[m.end() : m.end()+4500]
        # Si hay lista + oferta, el $ más alto suele ser el PVP base.
        precios = [clp(x) for x in RE_PRICE_DOLLAR.findall(after)]
        precios = [p for p in precios if p]
        precio = max(precios) if precios else None
        if precio is None:
            mval = RE_VALUE.search(after)
            if mval:
                precio = clp(mval.group(1))
        if not precio:
            continue
        href = m.group("href").strip()
        fuente = href if href.startswith("http") else BASE + href
        mpid = RE_PID.search(after)
        pid = (mpid.group(1) if mpid else href.rstrip("/").split("/")[-1] or href)
        pid = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(pid))[:80]
        if not pid:
            continue
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
        avail_blob = after.lower()
        agotado = bool(RE_UNAVAIL.search(after)) or (
            "out of stock" in avail_blob or "agotado" in avail_blob or "sin stock" in avail_blob
        )
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
        for alias in queries_es(med, PAIS):
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
    print(" CL Farmacias Ahumada → medicamentos_altos_costos_america")
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
        f"Chile Ahumada: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
