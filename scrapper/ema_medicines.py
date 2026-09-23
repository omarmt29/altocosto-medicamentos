"""
Descarga el catálogo oficial EMA (XLSX medicines) y lo cruza con DAMAC/FOMAC.

Fuente:
  https://www.ema.europa.eu/en/medicines/download-medicine-data
  medicines-output-medicines-report_en.xlsx

Uso:
    python scrapper/ema_medicines.py
    python scrapper/ema_medicines.py --fresh
    python scrapper/ema_medicines.py --n 6
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import coincide, norm  # noqa: E402
from scrapper.repositorio_ema import (  # noqa: E402
    asegurar_tabla,
    guardar_filas,
    purgar_combinados_en_principios_unicos,
    purgar_obsoletos,
)

UA = "SISALRIL-alto-costo/1.0 (research; contact: observatorio)"
XLSX_URL = (
    "https://www.ema.europa.eu/en/documents/report/"
    "medicines-output-medicines-report_en.xlsx"
)
CACHE = ROOT / "cache" / "ema"
FUENTE_PAGE = "https://www.ema.europa.eu/en/medicines/download-medicine-data"

COL_MAP = {
    "Category": "categoria",
    "Name of medicine": "nombre_medicamento",
    "EMA product number": "ema_product_number",
    "Medicine status": "medicine_status",
    "Opinion status": "opinion_status",
    "International non-proprietary name (INN) / common name": "inn",
    "Active substance": "active_substance",
    "Therapeutic area (MeSH)": "therapeutic_area",
    "Patient safety": "patient_safety",
    "ATC code (human)": "atc_code",
    "Pharmacotherapeutic group\n(human)": "pharmacotherapeutic_group",
    "Therapeutic indication": "therapeutic_indication",
    "Biosimilar": "es_biosimilar",
    "Generic": "es_generic",
    "Orphan medicine": "es_orphan",
    "Advanced therapy": "es_advanced_therapy",
    "Conditional approval": "es_conditional",
    "Additional monitoring": "additional_monitoring",
    "Marketing authorisation developer / applicant / holder": "mah",
    "Marketing authorisation date": "marketing_authorisation_date",
    "European Commission decision date": "ec_decision_date",
    "First published date": "first_published_date",
    "Last updated date": "last_updated_date",
    "Medicine URL": "medicine_url",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    return s


def _yes(val: Any) -> bool:
    s = str(val or "").strip().lower()
    return s in ("yes", "y", "true", "1", "sí", "si")


def _clean_html(txt: Any) -> str | None:
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return None
    s = str(txt).strip()
    if not s or s.lower() == "nan":
        return None
    s = re.sub(r"&nbsp;", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def _str(val: Any, max_len: int | None = None) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        s = val.strftime("%d/%m/%Y")
    elif isinstance(val, date):
        s = val.strftime("%d/%m/%Y")
    else:
        s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


def asegurar_xlsx(fresh: bool = False, sess: requests.Session | None = None) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "medicines-output-medicines-report_en.xlsx"
    if path.exists() and not fresh and path.stat().st_size > 50_000:
        return path
    sess = sess or _session()
    print(f"Descargando EMA medicines XLSX…", flush=True)
    r = sess.get(XLSX_URL, timeout=180)
    r.raise_for_status()
    path.write_bytes(r.content)
    print(f"  → {path} ({len(r.content):,} bytes)", flush=True)
    return path


def leer_medicines(path: Path) -> list[dict[str, Any]]:
    df = pd.read_excel(path, header=8)
    # normalizar nombres de columna (saltos de línea)
    rename = {}
    for c in df.columns:
        key = str(c)
        if key in COL_MAP:
            rename[c] = COL_MAP[key]
            continue
        # fallback sin newline
        key2 = key.replace("\n", " ").strip()
        for orig, dest in COL_MAP.items():
            if orig.replace("\n", " ").strip() == key2:
                rename[c] = dest
                break
    df = df.rename(columns=rename)
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        cat = _str(row.get("categoria"))
        if cat and cat.lower() != "human":
            continue
        nombre = _str(row.get("nombre_medicamento"), 500)
        ema_no = _str(row.get("ema_product_number"), 80) or ""
        if not nombre:
            continue
        if not ema_no:
            ema_no = f"NO-NUM/{norm(nombre)[:40]}"
        out.append(
            {
                "categoria": cat or "Human",
                "nombre_medicamento": nombre,
                "ema_product_number": ema_no,
                "medicine_status": _str(row.get("medicine_status"), 80),
                "opinion_status": _str(row.get("opinion_status"), 120),
                "inn": _str(row.get("inn"), 500),
                "active_substance": _str(row.get("active_substance"), 500),
                "therapeutic_area": _str(row.get("therapeutic_area"), 1000),
                "patient_safety": _yes(row.get("patient_safety")),
                "atc_code": _str(row.get("atc_code"), 80),
                "pharmacotherapeutic_group": _str(row.get("pharmacotherapeutic_group"), 300),
                "therapeutic_indication": _clean_html(row.get("therapeutic_indication")),
                "es_biosimilar": _yes(row.get("es_biosimilar")),
                "es_generic": _yes(row.get("es_generic")),
                "es_orphan": _yes(row.get("es_orphan")),
                "es_advanced_therapy": _yes(row.get("es_advanced_therapy")),
                "es_conditional": _yes(row.get("es_conditional")),
                "additional_monitoring": _yes(row.get("additional_monitoring")),
                "mah": _str(row.get("mah"), 500),
                "marketing_authorisation_date": _str(row.get("marketing_authorisation_date"), 40),
                "ec_decision_date": _str(row.get("ec_decision_date"), 40),
                "first_published_date": _str(row.get("first_published_date"), 40),
                "last_updated_date": _str(row.get("last_updated_date"), 40),
                "medicine_url": _str(row.get("medicine_url"), 500),
            }
        )
    return out


def _aliases_med(med: dict[str, Any]) -> list[str]:
    outs: list[str] = []
    for a in [str(med["nombre"]), *[str(x) for x in med.get("aliases") or []]]:
        n = norm(a)
        if len(n) >= 4:
            outs.append(n)
    seen: set[str] = set()
    uniq: list[str] = []
    for x in outs:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq


def _es_combinacion_lista(med: dict[str, Any]) -> bool:
    """DAMAC/FOMAC marca combinados con '/' (p. ej. Sofosbuvir/Velpatasvir)."""
    return "/" in str(med.get("nombre") or "")


def _es_combinacion_ema(row: dict[str, Any]) -> bool:
    """EMA separa principios de un combinado con ';' en INN / Active substance."""
    inn = str(row.get("inn") or "")
    substance = str(row.get("active_substance") or "")
    return ";" in inn or ";" in substance


def _match_ema(inn: str, substance: str, nombre: str, aliases: list[str]) -> bool:
    hay = " ".join(x for x in (inn, substance) if x)
    hn = norm(hay)
    brand = norm(nombre)
    if not hn and not brand:
        return False
    for a in aliases:
        if not a:
            continue
        if hn and re.search(rf"(^| ){re.escape(a)}( |$)", hn):
            return True
        if hn and len(a) >= 6 and re.search(rf"(^| ){re.escape(a)}[a-z0-9]*( |$)", hn):
            return True
        # biosimilares tipo adalimumab-xxxx no aplican en EMA, pero sí nombres compuestos
        if brand and a in brand and len(a) >= 5:
            return True
    return False


def cruzar_con_lista(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    catalogo = [(m, _aliases_med(m)) for m in MEDICAMENTOS]
    out: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in rows:
        inn = norm(row.get("inn") or "")
        substance = norm(row.get("active_substance") or "")
        nombre = str(row.get("nombre_medicamento") or "")
        ema_combo = _es_combinacion_ema(row)
        blob = " ".join(
            x
            for x in (
                row.get("inn"),
                row.get("active_substance"),
                row.get("nombre_medicamento"),
            )
            if x
        )
        for med, aliases in catalogo:
            lista_combo = _es_combinacion_lista(med)
            # Principio único de la lista ↔ solo EMA sin ';'.
            # Combinado de la lista ↔ solo EMA con ';' (p. ej. Akynzeo no entra en Palonosetrón).
            if lista_combo != ema_combo:
                continue
            if not _match_ema(inn, substance, nombre, aliases):
                continue
            if coincide(blob, med):
                out.append((med, row))
    return out


def filas_para_db(
    cruces: list[tuple[dict[str, Any], dict[str, Any]]],
    fecha_dato: date,
) -> list[dict[str, Any]]:
    etiqueta = fecha_dato.strftime("%Y-%m")
    filas: list[dict[str, Any]] = []
    for med, row in cruces:
        url = row.get("medicine_url") or ""
        if url and url.startswith("/"):
            url = "https://www.ema.europa.eu" + url
        filas.append(
            {
                "n_lista": int(med["n"]),
                "medicamento_lista": str(med["nombre"]),
                "programa": str(med.get("programa") or ""),
                "categoria": row.get("categoria"),
                "nombre_medicamento": row.get("nombre_medicamento") or "",
                "ema_product_number": row.get("ema_product_number") or "",
                "medicine_status": row.get("medicine_status"),
                "opinion_status": row.get("opinion_status"),
                "inn": row.get("inn"),
                "active_substance": row.get("active_substance"),
                "therapeutic_area": row.get("therapeutic_area"),
                "atc_code": row.get("atc_code"),
                "pharmacotherapeutic_group": row.get("pharmacotherapeutic_group"),
                "therapeutic_indication": row.get("therapeutic_indication"),
                "es_biosimilar": bool(row.get("es_biosimilar")),
                "es_generic": bool(row.get("es_generic")),
                "es_orphan": bool(row.get("es_orphan")),
                "es_advanced_therapy": bool(row.get("es_advanced_therapy")),
                "es_conditional": bool(row.get("es_conditional")),
                "additional_monitoring": bool(row.get("additional_monitoring")),
                "patient_safety": bool(row.get("patient_safety")),
                "mah": row.get("mah"),
                "marketing_authorisation_date": row.get("marketing_authorisation_date"),
                "ec_decision_date": row.get("ec_decision_date"),
                "first_published_date": row.get("first_published_date"),
                "last_updated_date": row.get("last_updated_date"),
                "medicine_url": url or None,
                "fuente_url": FUENTE_PAGE,
                "periodo_etiqueta": etiqueta,
                "fecha_dato": fecha_dato,
            }
        )
    return filas


def main() -> int:
    import urllib3

    urllib3.disable_warnings()
    ap = argparse.ArgumentParser(description="Ingestión EMA medicines → SQL")
    ap.add_argument("--fresh", action="store_true", help="Re-descargar XLSX")
    ap.add_argument("--n", type=int, default=None, help="Solo un n_lista (debug)")
    args = ap.parse_args()

    try:
        path = asegurar_xlsx(fresh=args.fresh)
        rows = leer_medicines(path)
        print(f"Medicamentos humanos EMA: {len(rows)}", flush=True)
        cruces = cruzar_con_lista(rows)
        if args.n is not None:
            cruces = [(m, r) for m, r in cruces if int(m["n"]) == int(args.n)]
        print(f"Cruces con lista DAMAC/FOMAC: {len(cruces)}", flush=True)
        fecha = date.today()
        filas = filas_para_db(cruces, fecha)
        asegurar_tabla()
        n = guardar_filas(filas)
        borrados = 0
        if filas:
            borrados = purgar_obsoletos(
                fecha,
                [
                    (
                        int(f["n_lista"]),
                        str(f["ema_product_number"]),
                        str(f["nombre_medicamento"]),
                    )
                    for f in filas
                ],
            )
        limpios = purgar_combinados_en_principios_unicos()
        por_n: dict[int, int] = {}
        for f in filas:
            por_n[int(f["n_lista"])] = por_n.get(int(f["n_lista"]), 0) + 1
        print(
            f"Guardadas {n} filas · obsoletos día: {borrados} · "
            f"combinados limpios: {limpios} · {len(por_n)} principios con match",
            flush=True,
        )
        top = sorted(por_n.items(), key=lambda x: -x[1])[:10]
        for nn, c in top:
            nombre = next((str(m["nombre"]) for m in MEDICAMENTOS if int(m["n"]) == nn), "?")
            print(f"  n={nn} {nombre}: {c}", flush=True)
        return 0
    except Exception as exc:
        print(f"ERROR ema_medicines: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
