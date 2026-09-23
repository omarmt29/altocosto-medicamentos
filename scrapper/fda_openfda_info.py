"""
Enriquece cada principio activo DAMAC/FOMAC con datos FDA.

- Indications and Usage (openFDA label)
- Genérico / biosimilar / intercambiable / referencia
- Tentative Approvals
- Patentes y exclusividades (Orange Book + Purple Book Patent List)

Uso:
    python scrapper/fda_openfda_info.py
    python scrapper/fda_openfda_info.py --n 6
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

ROOT_PATH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_PATH))
load_dotenv(ROOT_PATH / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.matching import norm  # noqa: E402
from scrapper.fda_patentes import patentes_orange_book, patentes_purple_book  # noqa: E402
from scrapper.repositorio_fda_info import asegurar_tabla, guardar_info  # noqa: E402
from scrapper.repositorio_purple import listar_por_n  # noqa: E402

UA = "SISALRIL-alto-costo/1.0 (research; contact: observatorio)"
OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"
OPENFDA_DRUGS = "https://api.fda.gov/drug/drugsfda.json"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json"})
    return s


def _get_json(sess: requests.Session, url: str) -> dict[str, Any] | None:
    try:
        r = sess.get(url, timeout=45)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _aliases_busqueda(med: dict[str, Any]) -> list[str]:
    outs: list[str] = []
    for a in [str(med["nombre"]), *[str(x) for x in med.get("aliases") or []]]:
        n = norm(a)
        if len(n) < 4:
            continue
        # openFDA usa mayúsculas / guiones
        outs.append(n.upper())
        outs.append(n.replace(" ", "-").upper())
        outs.append(n.replace(" ", "").upper())
    # únicos preservando orden
    seen: set[str] = set()
    uniq: list[str] = []
    for x in outs:
        if x in seen:
            continue
        seen.add(x)
        uniq.append(x)
    return uniq[:8]


def clasificar_tipo_licencia(tipo: str | None, fecha_inter: str | None) -> tuple[str, bool, bool]:
    t = (tipo or "").lower()
    inter_fecha = bool(fecha_inter and str(fecha_inter).strip().upper() not in ("", "N/A", "NA", "-"))
    if "interchangeable" in t or inter_fecha:
        return "intercambiable", True, True
    if "biosimilar" in t or "351(k)" in t:
        return "biosimilar", True, False
    if "351(a)" in t:
        return "referencia", False, False
    return "biologico", False, False


DRUGS_AT_FDA_OVERVIEW = (
    "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm"
    "?event=overview.process&ApplNo="
)


def _appl_no_digits(application_number: str) -> str:
    m = re.search(r"(\d+)", str(application_number or ""))
    return m.group(1) if m else ""


def _app_rank(application_number: str) -> int:
    """Prioriza NDA/BLA (marca / referencia) frente a ANDA genéricos."""
    app = str(application_number or "").upper()
    if app.startswith("BLA"):
        return 0
    if app.startswith("NDA"):
        return 1
    if app.startswith("ANDA"):
        return 3
    return 2


def fetch_latest_drugsfda_label_pdf(
    sess: requests.Session,
    aliases: list[str],
    application_numbers: set[str] | None = None,
) -> dict[str, str | None]:
    """Último Label (PDF) publicado en Drugs@FDA (accessdata) para el principio.

    Equivale al enlace «Label (PDF)» de la fila más reciente en Approval History
    (p. ej. NDA 021817 SUPPL-32 · 02/03/2026).
    """
    empty: dict[str, str | None] = {
        "pdf_url": None,
        "action_date": None,
        "application_number": None,
        "submission": None,
        "brand_name": None,
        "overview_url": None,
        "openfda_url": None,
    }
    seen_apps: set[str] = set()
    labels: list[dict[str, Any]] = []
    original_dates: dict[str, str] = {}

    exact_apps = {
        str(x).strip().upper()
        for x in (application_numbers or set())
        if str(x).strip()
    }
    searches = (
        [("application_number", app) for app in sorted(exact_apps)]
        if exact_apps
        else [
            (field, alias)
            for alias in aliases
            for field in ("openfda.substance_name", "openfda.generic_name", "openfda.brand_name")
        ]
    )

    for field, term in searches:
        hit_url = None
        data = None
        q = quote(f'{field}:"{term}"')
        hit_url = f"{OPENFDA_DRUGS}?search={q}&limit=100"
        data = _get_json(sess, hit_url)
        if not data or not data.get("results"):
            continue

        skip = 0
        total = int(((data.get("meta") or {}).get("results") or {}).get("total") or 0)
        while True:
            batch = data.get("results") or []
            if not batch:
                break
            for res in batch:
                app = str(res.get("application_number") or "").strip()
                if not app or app in seen_apps:
                    continue
                if exact_apps and app.upper() not in exact_apps:
                    continue
                seen_apps.add(app)
                of = res.get("openfda") or {}
                brands = of.get("brand_name") or []
                brand = brands[0] if isinstance(brands, list) and brands else None
                for sub in res.get("submissions") or []:
                    if str(sub.get("submission_type") or "").strip().upper() == "ORIG":
                        date_orig = str(sub.get("submission_status_date") or "").strip()
                        if date_orig:
                            old_orig = original_dates.get(app)
                            if not old_orig or date_orig < old_orig:
                                original_dates[app] = date_orig
                    for doc in sub.get("application_docs") or []:
                        if str(doc.get("type") or "").strip().lower() != "label":
                            continue
                        url = str(doc.get("url") or "").strip()
                        if not url:
                            continue
                        if url.startswith("http://"):
                            url = "https://" + url[len("http://") :]
                        date_s = str(sub.get("submission_status_date") or "").strip()
                        st = str(sub.get("submission_type") or "").strip()
                        sn = str(sub.get("submission_number") or "").strip()
                        labels.append(
                            {
                                "date": date_s,
                                "app": app,
                                "rank": _app_rank(app),
                                "submission": f"{st}-{sn}".strip("-"),
                                "brand": brand,
                                "url": url,
                            }
                        )
            skip += len(batch)
            if skip >= total or skip >= 300:
                break
            q_part = hit_url.split("search=", 1)[-1].split("&", 1)[0]
            data = _get_json(
                sess, f"{OPENFDA_DRUGS}?search={q_part}&limit=100&skip={skip}"
            )
            if not data:
                break

        if labels and not exact_apps:
            labels.sort(key=lambda x: (x["date"], -x["rank"]), reverse=True)
            # Misma fecha: preferir NDA/BLA (rank menor).
            best_date = labels[0]["date"]
            same = [x for x in labels if x["date"] == best_date]
            same.sort(key=lambda x: x["rank"])
            best = same[0]
            digits = _appl_no_digits(best["app"])
            return {
                "pdf_url": best["url"],
                "action_date": best["date"] or None,
                "application_number": best["app"],
                "submission": best["submission"] or None,
                "brand_name": best["brand"],
                "overview_url": (DRUGS_AT_FDA_OVERVIEW + digits) if digits else None,
                "openfda_url": hit_url,
            }
    if labels:
        # Entre varias aplicaciones de referencia, elegir la original aprobada
        # primero (ORIG más antiguo); luego tomar su Label con Action Date más reciente.
        apps_with_labels = {str(x["app"]).upper() for x in labels}
        preferred_app = min(
            apps_with_labels,
            key=lambda app: (
                original_dates.get(app, "99999999"),
                _app_rank(app),
                app,
            ),
        )
        labels = [x for x in labels if str(x["app"]).upper() == preferred_app]
        labels.sort(key=lambda x: x["date"], reverse=True)
        best = labels[0]
        digits = _appl_no_digits(best["app"])
        return {
            "pdf_url": best["url"],
            "action_date": best["date"] or None,
            "application_number": best["app"],
            "submission": best["submission"] or None,
            "brand_name": best["brand"],
            "overview_url": (DRUGS_AT_FDA_OVERVIEW + digits) if digits else None,
            "openfda_url": hit_url,
        }
    return empty


def fetch_indicaciones(sess: requests.Session, aliases: list[str]) -> dict[str, str | None]:
    """Indicaciones (texto SPL) + PDF oficial Drugs@FDA + ficha DailyMed.

    - Texto: openFDA Drug Label (SPL), SPL con effective_time más reciente.
    - PDF principal: último Label PDF de Drugs@FDA (accessdata), el de la
      Approval History (supplements / original).
    - DailyMed: ficha HTML / PDF SPL de respaldo.
    """
    empty = {
        "texto": None,
        "dailymed_url": None,
        "pdf_url": None,
        "dailymed_pdf_url": None,
        "openfda_url": None,
        "set_id": None,
        "effective_time": None,
        "version": None,
        "drugsfda_pdf_url": None,
        "drugsfda_action_date": None,
        "drugsfda_application_number": None,
        "drugsfda_submission": None,
        "drugsfda_overview_url": None,
    }
    drugsfda = fetch_latest_drugsfda_label_pdf(sess, aliases)

    for alias in aliases:
        q = quote(f'openfda.substance_name:"{alias}"')
        openfda_url = f"{OPENFDA_LABEL}?search={q}&sort=effective_time:desc&limit=5"
        data = _get_json(sess, openfda_url)
        if not data or not data.get("results"):
            q2 = quote(f'openfda.generic_name:"{alias}"')
            openfda_url = f"{OPENFDA_LABEL}?search={q2}&sort=effective_time:desc&limit=5"
            data = _get_json(sess, openfda_url)
        if not data or not data.get("results"):
            continue
        row = None
        txt = None
        for cand in data["results"]:
            ind = cand.get("indications_and_usage") or []
            cand_txt = ind[0] if isinstance(ind, list) and ind else (ind if isinstance(ind, str) else None)
            if cand_txt:
                row = cand
                txt = cand_txt
                break
        if not row or not txt:
            continue
        # limpiar numeración SPL típica
        txt = re.sub(r"^\s*\d+\s+INDICATIONS AND USAGE\s*", "INDICATIONS AND USAGE\n", txt, flags=re.I)
        set_id = str(row.get("set_id") or "").strip()
        if not set_id:
            spl = (row.get("openfda") or {}).get("spl_set_id") or []
            if isinstance(spl, list) and spl:
                set_id = str(spl[0]).strip()
        dailymed_url = None
        dailymed_pdf = None
        if set_id:
            dailymed_url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
            dailymed_pdf = (
                "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?"
                f"setid={set_id}&type=pdf&name=label.pdf"
            )
        else:
            dailymed_url = (
                "https://dailymed.nlm.nih.gov/dailymed/search.cfm?"
                f"labeltype=all&query={quote(alias)}"
            )
        pdf_principal = drugsfda.get("pdf_url") or dailymed_pdf
        return {
            "texto": txt.strip()[:8000],
            "dailymed_url": dailymed_url,
            "pdf_url": pdf_principal,
            "dailymed_pdf_url": dailymed_pdf,
            "openfda_url": openfda_url,
            "set_id": set_id or None,
            "effective_time": str(row.get("effective_time") or "").strip() or None,
            "version": str(row.get("version") or "").strip() or None,
            "drugsfda_pdf_url": drugsfda.get("pdf_url"),
            "drugsfda_action_date": drugsfda.get("action_date"),
            "drugsfda_application_number": drugsfda.get("application_number"),
            "drugsfda_submission": drugsfda.get("submission"),
            "drugsfda_overview_url": drugsfda.get("overview_url"),
        }

    # Sin texto SPL, igual devolver PDF Drugs@FDA si existe.
    if drugsfda.get("pdf_url"):
        return {
            **empty,
            "pdf_url": drugsfda.get("pdf_url"),
            "drugsfda_pdf_url": drugsfda.get("pdf_url"),
            "drugsfda_action_date": drugsfda.get("action_date"),
            "drugsfda_application_number": drugsfda.get("application_number"),
            "drugsfda_submission": drugsfda.get("submission"),
            "drugsfda_overview_url": drugsfda.get("overview_url"),
            "dailymed_url": drugsfda.get("overview_url"),
        }
    return empty


def resolver_fuentes_indicaciones(info: dict[str, Any] | None, sess: requests.Session | None = None) -> dict[str, Any]:
    """Normaliza enlaces de indicaciones (Drugs@FDA PDF / DailyMed / openFDA) para la UI."""
    if not info:
        return {}
    out = dict(info)
    u = str(out.get("fuente_indicaciones") or "").strip()
    pdf = str(out.get("fuente_indicaciones_pdf") or "").strip()
    api = str(out.get("fuente_indicaciones_api") or "").strip()

    # Preferir PDF ya resuelto de Drugs@FDA (accessdata label).
    if "drugsatfda_docs/label" in pdf.lower():
        if pdf.startswith("http://"):
            out["fuente_indicaciones_pdf"] = "https://" + pdf[len("http://") :]
        return out

    set_id = ""
    m = re.search(r"setid=([0-9a-fA-F-]{36})", u) or re.search(r"setid=([0-9a-fA-F-]{36})", pdf)
    if m:
        set_id = m.group(1)

    # Registros viejos: se guardó la URL del JSON de openFDA.
    if not set_id and ("api.fda.gov" in u or u.startswith(OPENFDA_LABEL)):
        api = api or u
        own = sess or _session()
        fetch_url = u if "api.fda.gov" in u else api
        # Preferir SPL más reciente si la URL antigua no traía sort.
        if "sort=" not in fetch_url:
            sep = "&" if "?" in fetch_url else "?"
            fetch_url = f"{fetch_url}{sep}sort=effective_time:desc"
        data = _get_json(own, fetch_url)
        if data and data.get("results"):
            row = None
            for cand in data["results"]:
                ind = cand.get("indications_and_usage") or []
                if (isinstance(ind, list) and ind) or isinstance(ind, str):
                    row = cand
                    break
            if not row:
                row = data["results"][0]
            set_id = str(row.get("set_id") or "").strip()
            if not set_id:
                spl = (row.get("openfda") or {}).get("spl_set_id") or []
                if isinstance(spl, list) and spl:
                    set_id = str(spl[0]).strip()

    if set_id:
        out["fuente_indicaciones"] = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}"
        # No pisar un PDF Drugs@FDA; DailyMed solo si aún no hay PDF.
        if not pdf or "dailymed" in pdf.lower():
            out["fuente_indicaciones_pdf"] = (
                "https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?"
                f"setid={set_id}&type=pdf&name=label.pdf"
            )
        if api:
            out["fuente_indicaciones_api"] = api
        elif "api.fda.gov" in u:
            out["fuente_indicaciones_api"] = u
        out["fuente_indicaciones_setid"] = set_id
    else:
        if u and "api.fda.gov" not in u:
            out["fuente_indicaciones"] = u
        if api:
            out["fuente_indicaciones_api"] = api
        if pdf:
            out["fuente_indicaciones_pdf"] = pdf
    return out


def fetch_tentative(sess: requests.Session, aliases: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _ingest(app: dict[str, Any], alias: str) -> None:
        app_no = str(app.get("application_number") or "")
        sponsor = app.get("sponsor_name") or ""
        brands = (app.get("openfda") or {}).get("brand_name") or []
        brand = brands[0] if brands else ""
        substances = (app.get("openfda") or {}).get("substance_name") or []
        marketing = {
            str(p.get("marketing_status") or "")
            for p in (app.get("products") or [])
        }
        sigue = any("tentative" in m.lower() for m in marketing)
        ta_subs = [
            s for s in (app.get("submissions") or [])
            if str(s.get("submission_status") or "").upper() == "TA"
        ]
        if not ta_subs and not sigue:
            return
        if not ta_subs:
            ta_subs = [{}]
        for sub in ta_subs:
            key = f"{app_no}|{sub.get('submission_number')}|{sub.get('submission_status_date')}|{sigue}"
            if key in seen:
                continue
            seen.add(key)
            docs = sub.get("application_docs") or []
            link = next((d.get("url") for d in docs if d.get("url")), None)
            out.append(
                {
                    "application_number": app_no,
                    "sponsor": sponsor,
                    "brand_name": brand,
                    "substance": substances[0] if substances else alias,
                    "submission_number": sub.get("submission_number"),
                    "submission_status_date": sub.get("submission_status_date"),
                    "review_priority": sub.get("review_priority"),
                    "marketing_status": sorted(m for m in marketing if m),
                    "posible_aprobacion": True,
                    "sigue_tentative": sigue,
                    "url": link,
                }
            )

    for alias in aliases[:4]:
        queries = [
            f'openfda.substance_name:"{alias}" AND submissions.submission_status:"TA"',
            f'openfda.substance_name:"{alias}" AND products.marketing_status:"None (Tentative Approval)"',
        ]
        for raw_q in queries:
            url = f"{OPENFDA_DRUGS}?search={quote(raw_q)}&limit=25"
            data = _get_json(sess, url)
            if not data:
                continue
            for app in data.get("results") or []:
                _ingest(app, alias)
            time.sleep(0.12)
    out.sort(
        key=lambda x: (
            bool(x.get("sigue_tentative")),
            str(x.get("submission_status_date") or ""),
        ),
        reverse=True,
    )
    return out[:40]


def fetch_generico_flag(sess: requests.Session, aliases: list[str]) -> bool:
    """True si openFDA reporta ANDA / productos no RLD para el principio."""
    for alias in aliases[:3]:
        q = quote(f'openfda.substance_name:"{alias}"')
        url = f"{OPENFDA_DRUGS}?search={q}&limit=15"
        data = _get_json(sess, url)
        if not data:
            continue
        for app in data.get("results") or []:
            app_no = str(app.get("application_number") or "").upper()
            if app_no.startswith("ANDA"):
                return True
            for p in app.get("products") or []:
                if str(p.get("reference_drug") or "").lower() == "no" and app_no.startswith("NDA"):
                    # NDA no referencia no implica genérico; ANDA sí
                    pass
        time.sleep(0.1)
    return False


def _proxima_fecha(valores: list[str | None]) -> str | None:
    parsed: list[tuple[date, str]] = []
    for raw in valores:
        if not raw:
            continue
        s = str(raw).strip()
        if not s or s.upper() in ("N/A", "NA", "-"):
            continue
        # formatos: July 23, 1986 | 25-Mar-25 | 2026-07-01
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d"):
            try:
                from datetime import datetime as dt

                d = dt.strptime(s.replace("  ", " "), fmt).date()
                parsed.append((d, s))
                break
            except ValueError:
                continue
    if not parsed:
        return None
    hoy = date.today()
    futuras = [p for p in parsed if p[0] >= hoy]
    pick = min(futuras, key=lambda x: x[0]) if futuras else max(parsed, key=lambda x: x[0])
    return pick[1]


def construir_info(med: dict[str, Any], sess: requests.Session, fecha_dato: date) -> dict[str, Any]:
    n = int(med["n"])
    aliases = _aliases_busqueda(med)
    aliases_norm = [norm(a) for a in aliases]
    aliases_norm = [a for a in aliases_norm if len(a) >= 4]
    # únicos
    seen_a: set[str] = set()
    aliases_norm = [a for a in aliases_norm if not (a in seen_a or seen_a.add(a))]

    purple = listar_por_n(n, solo_ultimo=True)
    es_biologico = bool(purple)
    tiene_ref = False
    tiene_bio = False
    tiene_inter = False
    exclus_pb: list[dict[str, Any]] = []
    for f in purple:
        clase, bio, inter = clasificar_tipo_licencia(f.get("tipo_licencia"), f.get("fecha_intercambio"))
        if clase == "referencia":
            tiene_ref = True
        if bio:
            tiene_bio = True
        if inter:
            tiene_inter = True
        for campo, label in (
            ("exclusividad_expira", "Exclusivity Expiration"),
            ("exclusividad_intercambio_expira", "First Interchangeable Exclusivity"),
            ("exclusividad_ref_expira", "Reference Product Exclusivity"),
            ("exclusividad_orphan_expira", "Orphan Exclusivity"),
        ):
            val = f.get(campo)
            if not val:
                continue
            exclus_pb.append(
                {
                    "fuente": "purple_book",
                    "tipo": label,
                    "nombre_comercial": f.get("nombre_comercial"),
                    "bla_number": f.get("bla_number"),
                    "expiration_text": val,
                    "expiration_date": None,
                    "estado": "informativa",
                    "fuente_url": f.get("fuente_url") or "https://purplebooksearch.fda.gov/",
                }
            )

    ind_meta = fetch_indicaciones(sess, aliases)
    ind = ind_meta.get("texto")
    ind_url = ind_meta.get("dailymed_url")
    ind_pdf = ind_meta.get("pdf_url")
    ind_pdf_dailymed = ind_meta.get("dailymed_pdf_url")
    ind_pdf_drugsfda = ind_meta.get("drugsfda_pdf_url")
    ind_api = ind_meta.get("openfda_url")
    ind_setid = ind_meta.get("set_id")
    ind_effective = ind_meta.get("effective_time")
    ind_drugsfda_date = ind_meta.get("drugsfda_action_date")
    ind_drugsfda_app = ind_meta.get("drugsfda_application_number")
    ind_drugsfda_sub = ind_meta.get("drugsfda_submission")
    ind_drugsfda_overview = ind_meta.get("drugsfda_overview_url")
    tentative = fetch_tentative(sess, aliases)
    generico = False if es_biologico else fetch_generico_flag(sess, aliases)

    ob = patentes_orange_book(aliases_norm, sess=sess)
    pb_pat = patentes_purple_book(aliases_norm, sess=sess)

    patentes = list(pb_pat.get("patentes") or []) + list(ob.get("patentes") or [])
    # dedupe por patent_no + appl/bla
    seen_p: set[str] = set()
    pats_uniq: list[dict[str, Any]] = []
    for p in patentes:
        key = f"{p.get('fuente')}|{p.get('patent_no')}|{p.get('appl_no') or p.get('bla_number')}|{p.get('expiration_date')}"
        if key in seen_p:
            continue
        seen_p.add(key)
        pats_uniq.append(p)
    pats_uniq.sort(key=lambda x: (x.get("estado") != "vigente", x.get("expiration_date") or "9999"))

    exclusividades = list(ob.get("exclusividades") or []) + exclus_pb
    productos = list(ob.get("productos") or [])

    patente_proxima = pb_pat.get("patente_proxima") or ob.get("patente_proxima")
    exclusividad_proxima = _proxima_fecha([e.get("expiration_text") for e in exclusividades])

    partes = []
    if es_biologico:
        if tiene_ref:
            partes.append("referencia 351(a)")
        if tiene_bio:
            partes.append("biosimilar")
        if tiene_inter:
            partes.append("intercambiable")
        if not partes:
            partes.append("biológico FDA")
    else:
        partes.append("molécula pequeña")
        if generico or any(p.get("clase") == "generico_anda" for p in productos):
            generico = True
            partes.append("con genéricos (ANDA)")
        else:
            partes.append("sin ANDA detectada / o solo marca")

    fuentes = [
        {
            "nombre": "FDA Purple Book (CSV mensual)",
            "url": "https://purplebooksearch.fda.gov/index.cfm?event=downloads",
        },
        {
            "nombre": "FDA Purple Book · Patent Lists",
            "url": "https://purplebooksearch.fda.gov/index.cfm?event=patentlist",
        },
        {
            "nombre": "FDA Orange Book data files",
            "url": "https://www.accessdata.fda.gov/scripts/cder/ob/",
        },
        {
            "nombre": "DailyMed · etiqueta SPL (indicaciones)",
            "url": ind_url or "https://dailymed.nlm.nih.gov/dailymed/",
        },
    ]
    if ind_pdf_drugsfda:
        fuentes.append(
            {
                "nombre": (
                    "Drugs@FDA · Label PDF (último"
                    + (f" · {ind_drugsfda_app} {ind_drugsfda_sub}" if ind_drugsfda_app else "")
                    + (f" · {ind_drugsfda_date}" if ind_drugsfda_date else "")
                    + ")"
                ),
                "url": ind_pdf_drugsfda,
            }
        )
    elif ind_pdf:
        fuentes.append(
            {
                "nombre": "Drugs@FDA / DailyMed · PDF de la etiqueta",
                "url": ind_pdf,
            }
        )
    if ind_pdf_dailymed and ind_pdf_dailymed != ind_pdf_drugsfda:
        fuentes.append(
            {
                "nombre": "DailyMed · PDF SPL (respaldo)",
                "url": ind_pdf_dailymed,
            }
        )
    if ind_drugsfda_overview:
        fuentes.append(
            {
                "nombre": "Drugs@FDA · Approval History",
                "url": ind_drugsfda_overview,
            }
        )
    fuentes.append(
        {
            "nombre": "openFDA Drug Labels (JSON origen)",
            "url": ind_api or "https://open.fda.gov/apis/drug/label/",
        }
    )
    fuentes.append(
        {
            "nombre": "openFDA Drugs@FDA",
            "url": "https://open.fda.gov/apis/drug/drugsfda/",
        }
    )

    return {
        "n_lista": n,
        "medicamento_lista": str(med["nombre"]),
        "programa": str(med.get("programa") or ""),
        "indicaciones_uso": ind,
        "fuente_indicaciones": ind_url,
        "fuente_indicaciones_pdf": ind_pdf,
        "fuente_indicaciones_api": ind_api,
        "fuente_indicaciones_setid": ind_setid,
        "fuente_indicaciones_effective_time": ind_effective,
        "fuente_indicaciones_drugsfda_date": ind_drugsfda_date,
        "fuente_indicaciones_drugsfda_app": ind_drugsfda_app,
        "es_biologico": es_biologico,
        "tiene_referencia": tiene_ref,
        "tiene_biosimilar": tiene_bio,
        "tiene_intercambiable": tiene_inter,
        "tiene_generico": generico,
        "resumen_clase": " · ".join(partes),
        "exclusividad_proxima": exclusividad_proxima,
        "patente_proxima": patente_proxima,
        "tentative_json": tentative,
        "patentes_json": pats_uniq,
        "exclusividades_json": exclusividades,
        "productos_fda_json": productos[:80],
        "fuentes_json": fuentes,
        "fuente_url": "https://purplebooksearch.fda.gov/" if es_biologico else "https://www.accessdata.fda.gov/scripts/cder/ob/",
        "periodo_etiqueta": purple[0].get("periodo_etiqueta") if purple else fecha_dato.strftime("%Y-%m"),
        "fecha_dato": purple[0]["fecha_dato"] if purple else fecha_dato.isoformat(),
    }


def correr(*, solo_n: int | None = None) -> dict[str, Any]:
    asegurar_tabla()
    sess = _session()
    hoy = date.today().replace(day=1)
    meds = MEDICAMENTOS
    if solo_n is not None:
        meds = [m for m in MEDICAMENTOS if int(m["n"]) == solo_n]
    ok = 0
    for i, med in enumerate(meds, 1):
        info = construir_info(med, sess, hoy)
        guardar_info(info)
        ok += 1
        tent = len(info.get("tentative_json") or [])
        print(
            f"[{i}/{len(meds)}] n={info['n_lista']} {info['medicamento_lista']}: "
            f"{'IND' if info.get('indicaciones_uso') else 'sin-IND'} · "
            f"{info.get('resumen_clase')} · TA={tent} · "
            f"pat={len(info.get('patentes_json') or [])}"
        )
        time.sleep(0.2)
    alertas = None
    try:
        from scrapper.alertas_patentes import detectar_fda

        alertas = detectar_fda(fecha_actual=hoy, hoy=date.today())
        print(f"Alertas patentes FDA: {alertas.get('mensaje')}")
    except Exception as exc:
        print(f"AVISO alertas patentes: {exc}", file=sys.stderr)
        alertas = {"ok": False, "error": str(exc)}
    return {"ok": True, "guardados": ok, "alertas_patentes": alertas}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Enriquecer principios activos con openFDA")
    p.add_argument("--n", type=int, default=None, help="Solo un n_lista")
    args = p.parse_args(argv)
    try:
        correr(solo_n=args.n)
    except Exception as exc:
        print(f"ERROR fda_openfda_info: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
