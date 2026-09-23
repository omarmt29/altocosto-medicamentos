"""Scraper PY · Punto Farma (payload SSR de búsqueda)."""

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

CACHE = ROOT / "cache" / "farmacias" / "puntofarma_py"
BASE = "https://www.puntofarma.com.py"
PAIS = "Paraguay"
FARMACIA = "Punto Farma"
MONEDA = "PYG"
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
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _parse_array_json(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _extraer_array_balanceado(texto: str, ini: int, *, escaped_quotes: bool = False) -> str | None:
    """Extrae un array JSON balanceado.

    Si escaped_quotes=True, las comillas del payload vienen como \\\" (Next.js flight).
    """
    depth = 0
    in_str = False
    i = ini
    n = len(texto)
    while i < n:
        if escaped_quotes:
            if in_str:
                if texto.startswith("\\\\", i):
                    i += 2
                    continue
                if texto.startswith('\\"', i):
                    in_str = False
                    i += 2
                    continue
                i += 1
                continue
            if texto.startswith('\\"', i):
                in_str = True
                i += 2
                continue
        else:
            if in_str:
                if texto[i] == "\\":
                    i += 2
                    continue
                if texto[i] == '"':
                    in_str = False
                    i += 1
                    continue
                i += 1
                continue
            if texto[i] == '"':
                in_str = True
                i += 1
                continue

        ch = texto[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return texto[ini : i + 1]
        i += 1
    return None


def _unescape_json_fragment(raw: str) -> str:
    """Convierte un fragmento con comillas escapadas (\\\") a JSON plano."""
    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == "\\" and i + 1 < n:
            nxt = raw[i + 1]
            if nxt == '"':
                out.append('"')
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
            if nxt == "/":
                out.append("/")
                i += 2
                continue
            if nxt == "u" and i + 5 < n:
                try:
                    out.append(chr(int(raw[i + 2 : i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            if nxt in "ntrbf":
                out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}[nxt])
                i += 2
                continue
        out.append(raw[i])
        i += 1
    return "".join(out)


def _extraer_array_productos(html: str) -> list[dict[str, Any]]:
    # Payload Next.js a veces viene plano y a veces escapado (\"productos\":[...).
    pos = html.find('"productos":[')
    if pos >= 0:
        ini = html.find("[", pos)
        raw = _extraer_array_balanceado(html, ini, escaped_quotes=False) if ini >= 0 else None
        if raw:
            data = _parse_array_json(raw)
            if data:
                return data

    pos = html.find('\\"productos\\":[')
    if pos >= 0:
        ini = html.find("[", pos)
        raw = _extraer_array_balanceado(html, ini, escaped_quotes=True) if ini >= 0 else None
        if raw:
            data = _parse_array_json(_unescape_json_fragment(raw))
            if data:
                return data
    return []


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
        r = s.get(f"{BASE}/buscar?s={quote(alias)}", timeout=TIMEOUT)
        if r.status_code in (401, 403, 429, 451):
            return [], datetime.now().date().isoformat(), f"bloqueado HTTP {r.status_code}"
        r.raise_for_status()
    except requests.RequestException as exc:
        return [], datetime.now().date().isoformat(), str(exc)
    productos = _extraer_array_productos(r.text)
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
        nombre = str(prod.get("descripcion") or "").strip()
        pid = str(prod.get("codigo") or "").strip()
        if not nombre or not pid:
            continue
        marca = ((prod.get("marca") or {}) if isinstance(prod.get("marca"), dict) else {})
        cat = ((prod.get("categoria") or {}) if isinstance(prod.get("categoria"), dict) else {})
        blob = " ".join(
            str(x or "")
            for x in [nombre, prod.get("descripcionLarga"), marca.get("descripcion"), cat.get("descripcion")]
        )
        seed_match = seed_match_for_med(blob, PAIS, med)
        if not coincide(blob, med) and not seed_match:
            continue
        try:
            precio = float(prod.get("precio") or 0)
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
            "principios_activos": [prod.get("descripcionLarga"), marca.get("descripcion")],
            "tipo_presentacion": nombre,
            "laboratorio": marca.get("descripcion") or "",
        }
        med2, calidad, obs = clasificar(med, p_fake)
        if seed_match and calidad == "ok":
            calidad = "revisar"
        if seed_match:
            extra_obs = f"Coincidencia impulsada por faltantes {PAIS} del reporte Digemaps"
            obs = f"{obs} | {extra_obs}" if obs else extra_obs
        ficha = parse_ficha(f"{nombre} {prod.get('descripcionLarga') or ''}", med2)
        out.append(
            {
                "pais": PAIS,
                "farmacia": FARMACIA,
                "fuente_url": f"{BASE}/buscar?s={quote(nombre)}"[:500],
                "id_producto_farmacia": pid[:80],
                "sku": str(prod.get("codigoBarra") or pid)[:80],
                "n_lista": int(med2["n"]),
                "medicamento_lista": str(med2["nombre"]),
                "programa": str(med2["programa"]),
                "nombre_comercial": nombre[:500],
                "principio_activo": ficha.get("principio_activo"),
                "concentracion": ficha.get("concentracion"),
                "presentacion": ficha.get("presentacion"),
                "laboratorio": ficha.get("laboratorio") or (marca.get("descripcion") or None),
                "precio": precio,
                "moneda": MONEDA,
                "disponibilidad": "Agotado" if str(prod.get("descontinuado") or "").upper() == "S" else "Disponible",
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
    print(" PY Punto Farma → medicamentos_altos_costos_america")
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
