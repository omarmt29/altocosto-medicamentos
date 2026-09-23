"""
Scraper AR · AlfaBeta (Manual Farmacéutico) → medicamentos_altos_costos_america

Catálogo público de PVP de referencia en farmacias argentinas.
Útil para moléculas de altísima especialidad sin e-commerce (p. ej. Naglazyme).

Uso:
    python scrapper/ar_alfabeta.py
    python scrapper/ar_alfabeta.py --fresh
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.ficha import parse_ficha  # noqa: E402
from scrapper.matching import clasificar  # noqa: E402
from scrapper.repositorio import asegurar_tabla, contar, guardar_filas, purgar_obsoletos  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "alfabeta"
BASE = "https://www.alfabeta.net"
PAIS = "Argentina"
FARMACIA = "AlfaBeta"
MONEDA = "ARS"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PAUSA = 0.9
TIMEOUT = 35

# Marcas comerciales prioritarias (slug AlfaBeta = nombre de producto).
_MARCAS_PRIORIDAD = {
    7: ["fabrazyme", "replagal"],
    35: ["naglazyme"],
    40: ["cerezyme"],
    51: ["gazyva", "gazyvaro"],
    84: ["blincyto"],
    86: ["evrysdi"],
}


def slugify(alias: str) -> str:
    s = unicodedata.normalize("NFKD", alias.strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def parse_ars(raw: str) -> float | None:
    t = re.sub(r"[^\d.,]", "", str(raw or ""))
    if not t:
        return None
    # 10.697.178,25 → 10697178.25
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        n = float(t)
    except ValueError:
        return None
    return n if n > 0 else None


def slugs_para(med: dict[str, Any]) -> list[str]:
    """Marcas primero (URL /precio/{marca}.html), luego resto de aliases."""
    out: list[str] = []
    seen: set[str] = set()
    n = int(med.get("n") or 0)
    nombre_slug = slugify(str(med.get("nombre") or ""))
    candidatos: list[str] = []
    candidatos.extend(_MARCAS_PRIORIDAD.get(n, []))
    for raw in med.get("aliases") or []:
        candidatos.append(str(raw))
    # Preferir aliases “de marca” (distintos del nombre INN) antes que el INN.
    inn_first = []
    brand_first = []
    for raw in candidatos:
        slug = slugify(raw)
        if len(slug) < 4:
            continue
        if slug == nombre_slug or slug.startswith(nombre_slug[:8] if len(nombre_slug) >= 8 else nombre_slug):
            inn_first.append(slug)
        else:
            brand_first.append(slug)
    for slug in brand_first + inn_first:
        if slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
    return out


def cache_path(slug: str) -> Path:
    return CACHE / f"{slug}.html"


def parse_presentaciones(html: str) -> list[tuple[str, float, str | None]]:
    out: list[tuple[str, float, str | None]] = []
    for m in re.finditer(
        r'class="tddesc">(.*?)</td>\s*<td class="tdprecio">([^<]+)</td>'
        r'(?:\s*<td class="tdfecha">\(([^)]*)\)</td>)?',
        html,
        re.S | re.I,
    ):
        desc = re.sub(r"<[^>]+>", " ", m.group(1))
        desc = re.sub(r"\s+", " ", desc).strip()
        precio = parse_ars(m.group(2))
        fecha = (m.group(3) or "").strip() or None
        if desc and precio:
            out.append((desc, precio, fecha))
    return out


def bajar_ficha(session: requests.Session, slug: str, *, forzar: bool) -> str | None:
    path = cache_path(slug)
    if not forzar and path.exists() and path.stat().st_size > 500:
        cached = path.read_text(encoding="utf-8", errors="ignore")
        if parse_presentaciones(cached):
            return cached
    url = f"{BASE}/precio/{quote(slug)}.html"
    time.sleep(PAUSA)
    try:
        r = session.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        print(f"  aviso {slug}: {exc}")
        return None
    if r.status_code != 200 or len(r.text) < 500:
        return None
    # Sin PVP: inexistente o paywall/rate-limit (HTML 200 sin precios).
    if not parse_presentaciones(r.text):
        return None
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(r.text, encoding="utf-8")
    return r.text


def lab_de(html: str) -> str | None:
    m2 = re.search(
        r"(Gobbi|BioMarin|Genzyme|Roche|Novartis|Sanofi|Pfizer|Janssen|Amgen|Bayer|AstraZeneca)",
        html,
        re.I,
    )
    return m2.group(1) if m2 else None


def nombre_comercial(html: str, slug: str) -> str:
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S | re.I)
    if m:
        mm = re.search(r'"name"\s*:\s*"([^"]+)"', m.group(1))
        if mm:
            return mm.group(1).strip()
    m = re.search(r"<title>\s*([^<\n]+?)\s*PRECIO", html, re.I)
    if m:
        return m.group(1).strip()
    return slug.upper()


def recolectar(*, forzar: bool = False) -> list[dict[str, Any]]:
    session = requests.Session()
    session.verify = False
    session.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.6",
            "Referer": f"{BASE}/precio/",
        }
    )
    fecha_dato = datetime.now().date().isoformat()
    filas: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()

    for med in MEDICAMENTOS:
        n_antes = len(filas)
        for slug in slugs_para(med):
            html = bajar_ficha(session, slug, forzar=forzar)
            if not html:
                continue
            presentaciones = parse_presentaciones(html)
            if not presentaciones:
                continue
            marca = nombre_comercial(html, slug)
            lab = lab_de(html)
            for i, (pres, precio, fecha_pub) in enumerate(presentaciones):
                nombre = f"{marca} {pres}".strip()
                pid = f"{slug}-{i+1}"[:80]
                clave = (pid, int(med["n"]))
                if clave in vistos:
                    continue
                fake = {
                    "nombre": nombre,
                    "principios_activos": [str(med["nombre"])],
                    "tipo_presentacion": pres,
                    "laboratorio": lab or "",
                }
                med2, calidad, obs = clasificar(med, fake)
                ficha = parse_ficha(nombre, med2)
                if lab and not ficha.get("laboratorio"):
                    ficha["laboratorio"] = lab
                vistos.add(clave)
                filas.append(
                    {
                        "pais": PAIS,
                        "farmacia": FARMACIA,
                        "fuente_url": f"{BASE}/precio/{slug}.html"[:500],
                        "id_producto_farmacia": pid,
                        "sku": pid,
                        "n_lista": int(med2["n"]),
                        "medicamento_lista": str(med2["nombre"]),
                        "programa": str(med2["programa"]),
                        "nombre_comercial": nombre[:500],
                        "principio_activo": ficha.get("principio_activo"),
                        "concentracion": ficha.get("concentracion") or None,
                        "presentacion": ficha.get("presentacion") or pres[:200],
                        "laboratorio": ficha.get("laboratorio") or lab,
                        "precio": precio,
                        "moneda": MONEDA,
                        "disponibilidad": "Consultar",
                        "calidad": calidad,
                        "observacion": obs,
                        "fecha_publicacion": None,
                        "fecha_dato": fecha_dato,
                    }
                )
            # Una ficha de marca basta por molécula (evita aliases redundantes)
            if len(filas) > n_antes:
                break
        n_nuevas = len(filas) - n_antes
        marca = "·" if n_nuevas else " "
        print(f"  {marca} {n_nuevas:3d}  {med['nombre']}")
    return filas


def main() -> int:
    forzar = "--fresh" in sys.argv
    print("=" * 64)
    print(" AR AlfaBeta (Manual Farmacéutico) → medicamentos_altos_costos_america")
    print("=" * 64)
    filas = recolectar(forzar=forzar)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista DAMAC/FOMAC: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos(
            PAIS,
            FARMACIA,
            [(f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"AR AlfaBeta: {contar(PAIS, FARMACIA)} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
