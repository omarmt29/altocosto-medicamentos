"""
Scraper RD · Farmacia Carol → P_aguila.medicamentos_altos_costos_america

Búsqueda pública de la tienda VevoCart (https://tienda.farmaciacarol.com)
con PVP en DOP y enlace a la ficha.

Uso:
    python scrapper/rd_carol.py
    python scrapper/rd_carol.py --fresh
    python scrapper/rd_carol.py --fomac
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import clasificar, medicamentos_que_pegan  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "carol"
BASE = "https://tienda.farmaciacarol.com"
PAIS = "República Dominicana"
FARMACIA = "Carol"
MONEDA = "DOP"
PAUSA = 0.2
TIMEOUT = 45
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-DO,es;q=0.9,en;q=0.7",
        }
    )
    return s


def queries_carol(med: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in med["aliases"]:
        q = str(raw).strip()
        if len(q) < 5:
            continue
        k = q.lower()
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out


def cache_path(alias: str) -> Path:
    safe = re.sub(r"[^a-z0-9]+", "_", alias.lower())[:80] or "q"
    return CACHE / f"{safe}.json"


def parse_precio(texto: str | None) -> float | None:
    if not texto:
        return None
    s = str(texto).replace("RD$", "").replace("$", "").replace(" ", "")
    s = s.replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    n = float(m.group(1))
    return n if n > 0 else None


def parse_listado(html: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for m in re.finditer(r'uxProductIDHidden" value="(\d+)"', html):
        pid = m.group(1)
        if pid in vistos:
            continue
        vistos.add(pid)
        chunk = html[max(0, m.start() - 3200) : m.end() + 400]
        href_m = re.search(r'class="ProductLink" href="([^"]+)"', chunk)
        name_m = re.search(
            r'class="myLink[^"]*"\s+tag_url="[^"]*"\s*>\s*([^<]+)',
            chunk,
        )
        if not name_m:
            name_m = re.search(
                r'class="CommonProductName"\s*>\s*<a[^>]*>\s*([^<]+)',
                chunk,
            )
        price_m = re.search(
            r'class="OurPriceValue">\s*<span[^>]*>\s*([^<]+)',
            chunk,
        )
        stock_m = re.search(r'uxStockLabel[^>]*>([^<]*)', chunk)
        stock_txt = (stock_m.group(1) if stock_m else "").strip().lower()
        href = (href_m.group(1) if href_m else "").strip()
        if href.startswith("~/"):
            href = href[2:]
        nombre = (name_m.group(1) if name_m else "").strip()
        precio = parse_precio(price_m.group(1) if price_m else None)
        if "agotado" in stock_txt or "out of stock" in stock_txt:
            disp = "Agotado"
        elif precio:
            disp = "Disponible"
        else:
            disp = "Consultar"
        url = urljoin(BASE + "/", href) if href else BASE
        items.append(
            {
                "id": pid,
                "nombre": nombre,
                "precio": precio,
                "url": url,
                "disponibilidad": disp,
            }
        )
    return items


def buscar(s: requests.Session, alias: str, *, forzar: bool) -> list[dict[str, Any]]:
    path = cache_path(alias)
    if not forzar and path.exists() and path.stat().st_size >= 2:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    url = (
        f"{BASE}/advancedsearchresult.aspx"
        f"?keyword={quote(alias)}&quick=true&searchtype="
    )
    html = ""
    for intento in range(4):
        r = s.get(url, timeout=TIMEOUT)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(1.5 * (intento + 1))
            continue
        r.raise_for_status()
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        html = r.text
        break
    items = parse_listado(html) if html else []
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    time.sleep(PAUSA)
    return items


def filas_para_db(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for h in hits:
        nombre = (h.get("nombre") or "").strip()
        url = h.get("url") or ""
        if not nombre or not h.get("precio"):
            continue
        texto = f"{nombre} {url}"
        meds = medicamentos_que_pegan(texto)
        if not meds:
            continue
        fake = {
            "nombre": nombre,
            "principios_activos": [],
            "principios_activos_con_dosaje": [],
            "tipo_presentacion": nombre,
            "palabras_clave": url,
        }
        for med0 in meds:
            med, calidad, obs = clasificar(med0, fake)
            n_lista = int(med["n"])
            pid = str(h.get("id") or "")
            if not pid:
                continue
            clave = (pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(nombre, med)
            out.append(
                {
                    "pais": PAIS,
                    "farmacia": FARMACIA,
                    "fuente_url": str(url)[:500],
                    "id_producto_farmacia": pid[:80],
                    "sku": pid[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": ficha.get("principio_activo"),
                    "concentracion": ficha.get("concentracion"),
                    "presentacion": ficha.get("presentacion"),
                    "laboratorio": ficha.get("laboratorio"),
                    "precio": h.get("precio"),
                    "moneda": MONEDA,
                    "disponibilidad": h.get("disponibilidad") or "Disponible",
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def recolectar(s: requests.Session, *, forzar: bool, meds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    productos: list[dict[str, Any]] = []
    vistos_id: set[str] = set()
    queries: list[str] = []
    vistos_q: set[str] = set()
    for med in meds:
        for q in queries_carol(med):
            k = q.lower()
            if k in vistos_q:
                continue
            vistos_q.add(k)
            queries.append(q)
    print(f"Búsquedas Carol: {len(queries)}")
    for i, q in enumerate(queries, start=1):
        try:
            lote = buscar(s, q, forzar=forzar)
        except Exception as exc:
            print(f"  [{i}/{len(queries)}] {q}: error {exc}")
            continue
        n_ok = 0
        for it in lote:
            pid = str(it.get("id") or "")
            if not pid or pid in vistos_id:
                continue
            vistos_id.add(pid)
            productos.append(it)
            n_ok += 1
        if n_ok:
            print(f"  [{i}/{len(queries)}] {q}: {n_ok} producto(s)")
        elif i % 25 == 0:
            print(f"  [{i}/{len(queries)}] …")
    return productos


def main() -> int:
    forzar = "--fresh" in sys.argv
    solo_fomac = "--fomac" in sys.argv
    meds = MEDICAMENTOS
    if solo_fomac:
        meds = [m for m in MEDICAMENTOS if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" RD Farmacia Carol → medicamentos_altos_costos_america")
    if solo_fomac:
        print(f" Solo FOMAC ({len(meds)} moléculas)")
    print("=" * 64)
    CACHE.mkdir(parents=True, exist_ok=True)
    s = session()
    hits = recolectar(s, forzar=forzar, meds=meds)
    print(f"Productos Carol únicos: {len(hits)}")
    filas = filas_para_db(hits)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Coincidencias lista: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    if solo_fomac or not filas:
        borrados = 0
    else:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"RD Carol: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
