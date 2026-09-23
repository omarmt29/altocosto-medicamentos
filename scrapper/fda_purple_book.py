"""
Scraper FDA Purple Book → P_aguila.medicamentos_fda_purple_book

Descarga el CSV mensual oficial, cruza Proper/Proprietary Name con la lista
DAMAC/FOMAC (por principio activo / alias) y guarda un snapshot con fecha_dato
mensual + fecha_registro para comparar periodos.

Uso:
    python scrapper/fda_purple_book.py
    python scrapper/fda_purple_book.py --fresh
    python scrapper/fda_purple_book.py --year 2026 --month 7
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from calendar import month_name
from datetime import date
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import coincide, norm  # noqa: E402
from scrapper.repositorio_purple import (  # noqa: E402
    asegurar_tabla,
    guardar_filas,
    resumen_cobertura,
)

CACHE = ROOT / "cache" / "purple_book"
DOWNLOADS_URL = "https://purplebooksearch.fda.gov/index.cfm?event=downloads"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Columnas del CSV (nombres varían ligeramente entre meses).
COL_MAP = {
    "n/r/u": "cambio_nr_u",
    "applicant": "solicitante",
    "bla number": "bla_number",
    "proprietary name": "nombre_comercial",
    "proper name": "nombre_propio",
    "license type": "tipo_licencia",
    "bla type": "tipo_licencia",
    "strength": "concentracion",
    "dosage form": "forma_dosificacion",
    "route of administration": "via_administracion",
    "product presentation": "presentacion",
    "marketing status": "estado_marketing",
    "licensure": "licensure",
    "approval date": "fecha_aprobacion",
    "inter. approval date": "fecha_intercambio",
    "interchangeable approval date": "fecha_intercambio",
    "interchangeable date": "fecha_intercambio",
    "date of interchangeability": "fecha_intercambio",
    "ref. product proper name": "ref_nombre_propio",
    "ref. product proprietary name": "ref_nombre_comercial",
    "supplement number": "supplement_number",
    "submission type": "submission_type",
    "license number": "license_number",
    "product number": "product_number",
    "center": "center",
    "date of first licensure": "fecha_primera_licencia",
    "exclusivity expiration date": "exclusividad_expira",
    "first interchangeable exclusivity exp. date": "exclusividad_intercambio_expira",
    "ref. product exclusivity exp. date": "exclusividad_ref_expira",
    "orphan exclusivity exp. date": "exclusividad_orphan_expira",
    "patent list provided": "patent_list",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    return s


def listar_csv_disponibles(sess: requests.Session | None = None) -> list[dict[str, Any]]:
    """Parsea la página de descargas FDA y lista CSV mensuales (más reciente primero)."""
    sess = sess or _session()
    r = sess.get(DOWNLOADS_URL, timeout=60)
    r.raise_for_status()
    html = r.text
    pat = re.compile(
        r'href="(https://www\.accessdata\.fda\.gov/drugsatfda_docs/PurpleBook/'
        r'(\d{4})/purplebook-search-([A-Za-z]+)-data-download\.csv)"',
        re.I,
    )
    meses = {m.lower(): i for i, m in enumerate(month_name) if m}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in pat.finditer(html):
        url, year_s, month_s = m.group(1), m.group(2), m.group(3)
        if url in seen:
            continue
        seen.add(url)
        year = int(year_s)
        month = meses.get(month_s.lower())
        if not month:
            continue
        etiqueta = f"{month_name[month]} {year}"
        out.append(
            {
                "url": url,
                "year": year,
                "month": month,
                "fecha_dato": date(year, month, 1),
                "periodo_etiqueta": etiqueta,
            }
        )
    out.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    return out


def elegir_csv(
    year: int | None = None,
    month: int | None = None,
    sess: requests.Session | None = None,
) -> dict[str, Any]:
    disponibles = listar_csv_disponibles(sess)
    if not disponibles:
        raise RuntimeError("No se encontraron CSV en la página de descargas Purple Book")
    if year and month:
        for item in disponibles:
            if item["year"] == year and item["month"] == month:
                return item
        # Fallback: construir URL (case-insensitive en servidor no garantizado)
        mname = month_name[month]
        for cand in (mname, mname.lower(), mname.capitalize()):
            url = (
                f"https://www.accessdata.fda.gov/drugsatfda_docs/PurpleBook/"
                f"{year}/purplebook-search-{cand}-data-download.csv"
            )
            return {
                "url": url,
                "year": year,
                "month": month,
                "fecha_dato": date(year, month, 1),
                "periodo_etiqueta": f"{mname} {year}",
            }
    return disponibles[0]


def descargar_csv(
    meta: dict[str, Any],
    *,
    fresh: bool = False,
    sess: requests.Session | None = None,
) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    name = f"purplebook-{meta['year']:04d}-{meta['month']:02d}.csv"
    path = CACHE / name
    if path.exists() and path.stat().st_size > 1000 and not fresh:
        return path
    sess = sess or _session()
    r = sess.get(meta["url"], timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def _leer_filas_csv(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    hdr_i = next(
        (i for i, line in enumerate(lines[:40]) if "BLA Number" in line and "Proper Name" in line),
        None,
    )
    if hdr_i is None:
        raise RuntimeError(f"No se encontró encabezado BLA Number en {path}")
    reader = csv.DictReader(io.StringIO("\n".join(lines[hdr_i:])))
    rows: list[dict[str, str]] = []
    for raw in reader:
        mapped: dict[str, str] = {}
        for k, v in raw.items():
            key = COL_MAP.get((k or "").strip().lower())
            if not key:
                continue
            mapped[key] = "" if v is None else str(v).strip()
        if mapped.get("bla_number") and mapped.get("bla_number").upper() != "BLA NUMBER":
            rows.append(mapped)
    return rows


def _blob_fila(row: dict[str, str]) -> str:
    return " | ".join(
        x
        for x in (
            row.get("nombre_propio"),
            row.get("nombre_comercial"),
            row.get("ref_nombre_propio"),
            row.get("ref_nombre_comercial"),
        )
        if x
    )


def _aliases_med(med: dict[str, Any]) -> list[str]:
    aliases = [norm(med["nombre"])] + [norm(a) for a in med["aliases"]]
    return [a for a in aliases if len(a) >= 4]


def _es_combinado_proper(nombre_propio: str) -> bool:
    """Coformulaciones Purple Book: 'X and hyaluronidase…' / varios APIs."""
    pn = (nombre_propio or "").lower()
    return " and " in pn or ";" in pn


def _match_purple(pn: str, brand: str, ref: str, aliases: list[str]) -> bool:
    """Match rápido por proper name (incl. sufijo biosimilar) o marca."""
    for a in aliases:
        if not a:
            continue
        if pn == a or pn.startswith(a + "-"):
            return True
        # "pembrolizumab and …" no es el mismo INN simple → se filtra en cruzar
        if pn.startswith(a + " ") and " and " not in pn and ";" not in pn:
            return True
        if brand == a or f" {a} " in f" {brand} " or brand.startswith(a + " "):
            return True
        if ref and (ref == a or ref.startswith(a + " ") or ref.startswith(a + "-")):
            return True
        # adalimumab-aqvh
        if len(pn) > len(a) + 2 and pn.startswith(a + "-") and pn[len(a) + 1 :].isalnum():
            return True
    return False


def cruzar_con_lista(rows: list[dict[str, str]]) -> list[tuple[dict[str, Any], dict[str, str]]]:
    """Devuelve pares (medicamento_lista, fila_purple)."""
    catalogo = [(m, _aliases_med(m)) for m in MEDICAMENTOS]
    out: list[tuple[dict[str, Any], dict[str, str]]] = []
    for row in rows:
        pn = norm(row.get("nombre_propio") or "")
        brand = norm(row.get("nombre_comercial") or "")
        ref = norm(
            " ".join(
                x
                for x in (row.get("ref_nombre_propio"), row.get("ref_nombre_comercial"))
                if x
            )
        )
        if not (pn or brand):
            continue
        blob = _blob_fila(row)
        for med, aliases in catalogo:
            lista_combo = "/" in str(med.get("nombre") or "")
            if _es_combinado_proper(pn) and not lista_combo:
                continue
            if not _match_purple(pn, brand, ref, aliases):
                continue
            if coincide(blob, med):
                out.append((med, row))
    return out


def filas_para_db(
    cruces: list[tuple[dict[str, Any], dict[str, str]]],
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    from scrapper.fda_openfda_info import clasificar_tipo_licencia

    filas: list[dict[str, Any]] = []
    for med, row in cruces:
        clase, bio, inter = clasificar_tipo_licencia(
            row.get("tipo_licencia"), row.get("fecha_intercambio")
        )
        filas.append(
            {
                "n_lista": int(med["n"]),
                "medicamento_lista": str(med["nombre"]),
                "programa": str(med.get("programa") or ""),
                "cambio_nr_u": row.get("cambio_nr_u"),
                "solicitante": row.get("solicitante"),
                "bla_number": row.get("bla_number") or "",
                "nombre_comercial": row.get("nombre_comercial"),
                "nombre_propio": row.get("nombre_propio"),
                "tipo_licencia": row.get("tipo_licencia"),
                "concentracion": row.get("concentracion"),
                "forma_dosificacion": row.get("forma_dosificacion"),
                "via_administracion": row.get("via_administracion"),
                "presentacion": row.get("presentacion"),
                "estado_marketing": row.get("estado_marketing"),
                "licensure": row.get("licensure"),
                "fecha_aprobacion": row.get("fecha_aprobacion"),
                "fecha_intercambio": row.get("fecha_intercambio"),
                "ref_nombre_propio": row.get("ref_nombre_propio"),
                "ref_nombre_comercial": row.get("ref_nombre_comercial"),
                "supplement_number": row.get("supplement_number"),
                "submission_type": row.get("submission_type"),
                "license_number": row.get("license_number"),
                "product_number": row.get("product_number") or "0",
                "center": row.get("center"),
                "fecha_primera_licencia": row.get("fecha_primera_licencia"),
                "exclusividad_expira": row.get("exclusividad_expira"),
                "exclusividad_intercambio_expira": row.get(
                    "exclusividad_intercambio_expira"
                ),
                "exclusividad_ref_expira": row.get("exclusividad_ref_expira"),
                "exclusividad_orphan_expira": row.get("exclusividad_orphan_expira"),
                "patent_list": row.get("patent_list"),
                "es_biosimilar": bio,
                "es_intercambiable": inter,
                "clase_producto": clase,
                "fuente_url": meta["url"],
                "periodo_etiqueta": meta["periodo_etiqueta"],
                "fecha_dato": meta["fecha_dato"],
            }
        )
    return filas


def correr(
    *,
    fresh: bool = False,
    year: int | None = None,
    month: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    sess = _session()
    meta = elegir_csv(year=year, month=month, sess=sess)
    path = descargar_csv(meta, fresh=fresh, sess=sess)
    rows = _leer_filas_csv(path)
    cruces = cruzar_con_lista(rows)
    filas = filas_para_db(cruces, meta)
    moleculas = sorted({f["n_lista"] for f in filas})
    print(
        f"Purple Book {meta['periodo_etiqueta']}: {len(rows)} filas FDA · "
        f"{len(filas)} cruces · {len(moleculas)} moléculas lista · archivo {path.name}"
    )
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "periodo": meta["periodo_etiqueta"],
            "filas_fda": len(rows),
            "cruces": len(filas),
            "moleculas": len(moleculas),
            "n_lista": moleculas,
        }
    tabla = asegurar_tabla()
    stats = guardar_filas(filas)
    cov = resumen_cobertura(meta["fecha_dato"])
    print(
        f"Guardado en {tabla}: upserts={stats['upserts']} · "
        f"periodo={cov.get('periodo_etiqueta')} · "
        f"filas={cov.get('filas')} · moléculas={cov.get('moleculas')}"
    )
    return {
        "ok": True,
        "periodo": meta["periodo_etiqueta"],
        "fecha_dato": meta["fecha_dato"].isoformat(),
        "url": meta["url"],
        "filas_fda": len(rows),
        "cruces": len(filas),
        "moleculas": len(moleculas),
        **stats,
        **cov,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scraper FDA Purple Book por principio activo")
    p.add_argument("--fresh", action="store_true", help="Re-descarga el CSV aunque haya caché")
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--month", type=int, default=None, help="1-12")
    p.add_argument("--dry-run", action="store_true", help="No escribe en SQL")
    args = p.parse_args(argv)
    try:
        correr(fresh=args.fresh, year=args.year, month=args.month, dry_run=args.dry_run)
    except Exception as exc:
        print(f"ERROR Purple Book: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
