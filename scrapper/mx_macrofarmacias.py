"""
Scraper MX · Macrofarmacias → P_aguila.medicamentos_altos_costos_america

Catálogo público de especialidad (https://macrofarmacias.com/catalogo.php).
Cruza con DAMAC/FOMAC y hace MERGE.

Uso:
    python scrapper/mx_macrofarmacias.py
    python scrapper/mx_macrofarmacias.py --fresh
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import clasificar, medicamentos_que_pegan  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.report_seeds import meds_por_reporte  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "macrofarmacias"
CACHE_FILE = CACHE / "catalogo.json"
BASE = "https://macrofarmacias.com"
PAIS = "México"
FARMACIA = "Macrofarmacias"
MONEDA = "MXN"
PAUSA = 0.3
TIMEOUT = 40
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
PRECIO_RE = re.compile(r"\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))")
PROD_RE = re.compile(
    r'<div class="cont-prod">(.*?)<button class="btn-cart">',
    re.I | re.S,
)


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Referer": BASE + "/",
        }
    )
    return s


def parse_precio(texto: str) -> float | None:
    m = PRECIO_RE.search(texto.replace("\xa0", " "))
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return n if n > 0 else None


def parse_pagina(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bloque in PROD_RE.findall(html):
        href_m = re.search(
            r'href="((?:https://macrofarmacias\.com)?/producto/(\d+)/[^"]+)"',
            bloque,
        )
        if not href_m:
            continue
        pid = href_m.group(2)
        url = urljoin(BASE + "/", href_m.group(1))
        nom_m = re.search(
            r'class="t-name-product"[^>]*>\s*<a[^>]*>([^<]+)',
            bloque,
            re.I,
        )
        precio_m = re.search(r'class="t-price-product"[^>]*>([^<]+)', bloque, re.I)
        img_m = re.search(r'src="(?:php/App/Resources/Productos/)?([^"]+)"', bloque)
        sku = ""
        if img_m:
            sku = Path(img_m.group(1)).stem
        nombre = (nom_m.group(1) if nom_m else "").strip()
        if not nombre:
            nombre = url.rstrip("/").split("/")[-1].replace("-", " ")
        out.append(
            {
                "id": pid,
                "url": url.split("?")[0][:500],
                "nombre": re.sub(r"\s+", " ", nombre),
                "precio": parse_precio(precio_m.group(1) if precio_m else ""),
                "sku": sku[:80],
            }
        )
    return out


def paginas_totales(html: str) -> int:
    nums = [int(x) for x in re.findall(r"[?&]pagina=(\d+)", html)]
    return max(nums) if nums else 1


def bajar_catalogo(forzar: bool = False) -> list[dict[str, Any]]:
    if CACHE_FILE.exists() and CACHE_FILE.stat().st_size > 100 and not forzar:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            print(f"Catálogo en caché: {len(data)} productos")
            return data
    s = session()
    print(f"Descargando catálogo Macrofarmacias ({BASE}/catalogo.php) …")
    r = s.get(f"{BASE}/catalogo.php", timeout=TIMEOUT)
    r.raise_for_status()
    n_pag = paginas_totales(r.text)
    vistos: dict[str, dict[str, Any]] = {}
    for pagina in range(1, n_pag + 1):
        if pagina > 1:
            time.sleep(PAUSA)
            r = s.get(f"{BASE}/catalogo.php", params={"pagina": pagina}, timeout=TIMEOUT)
            r.raise_for_status()
        lote = parse_pagina(r.text)
        for p in lote:
            vistos[p["id"]] = p
        print(f"  página {pagina}/{n_pag}: {len(lote)} · únicos {len(vistos)}")
    data = list(vistos.values())
    CACHE.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catálogo vivo: {len(data)} productos")
    return data


def filas_para_db(catalogo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()
    for p in catalogo:
        texto = f"{p.get('nombre') or ''} {p.get('url') or ''}"
        hits = medicamentos_que_pegan(texto)
        alias_hit_ns = {int(m["n"]) for m in hits}
        reporte_hits = meds_por_reporte(texto, PAIS)
        for med in reporte_hits:
            if int(med["n"]) not in alias_hit_ns:
                hits.append(med)
        if not hits:
            continue
        fake = {
            "nombre": p.get("nombre"),
            "principios_activos": [],
            "principios_activos_con_dosaje": [],
            "tipo_presentacion": p.get("nombre"),
        }
        for med0 in hits:
            seed_match = int(med0["n"]) not in alias_hit_ns
            med, calidad, obs = clasificar(med0, fake)
            if seed_match and calidad == "ok":
                calidad = "revisar"
            if seed_match:
                extra_obs = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
                obs = f"{obs} | {extra_obs}" if obs else extra_obs
            n_lista = int(med["n"])
            pid = str(p.get("id") or "")
            clave = (pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)
            ficha = parse_ficha(p.get("nombre") or "", med)
            out.append(
                {
                    "pais": PAIS,
                    "farmacia": FARMACIA,
                    "fuente_url": (p.get("url") or BASE)[:500],
                    "id_producto_farmacia": pid[:80],
                    "sku": (p.get("sku") or pid)[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": (p.get("nombre") or "")[:500],
                    "principio_activo": ficha.get("principio_activo"),
                    "concentracion": ficha.get("concentracion"),
                    "presentacion": ficha.get("presentacion"),
                    "laboratorio": ficha.get("laboratorio"),
                    "precio": p.get("precio"),
                    "moneda": MONEDA,
                    "disponibilidad": "Disponible" if p.get("precio") else "Consultar",
                    "calidad": calidad,
                    "observacion": obs,
                    "fecha_publicacion": None,
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" MX Macrofarmacias → medicamentos_altos_costos_america")
    print("=" * 64)
    catalogo = bajar_catalogo(forzar=forzar)
    filas = filas_para_db(catalogo)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista DAMAC/FOMAC: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = purgar_obsoletos(
        PAIS,
        FARMACIA,
        [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
    )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"MX Macrofarmacias: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
