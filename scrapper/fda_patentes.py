"""Patentes y exclusividades FDA (Orange Book + Purple Book Patent List)."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from scrapper.matching import norm

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "fda"
ORANGE_ZIP_URL = "https://www.fda.gov/media/76860/download"
PURPLE_PATENTS_URL = "https://purplebooksearch.fda.gov/index.cfm?event=patentlist"
ORANGE_SEARCH = "https://www.accessdata.fda.gov/scripts/cder/ob/"
ORANGE_PAGE = "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
UA = "SISALRIL-alto-costo/1.0 (research; contact: observatorio)"


def url_orange_producto(appl_type: str | None, appl_no: str | None) -> str | None:
    at = str(appl_type or "").strip().upper()
    an = str(appl_no or "").strip()
    if not at or not an:
        return None
    # Appl_No en Orange Book suele ir con ceros a la izquierda (6 dígitos)
    if an.isdigit():
        an = an.zfill(6)
    return (
        "https://www.accessdata.fda.gov/scripts/cder/ob/results_product.cfm"
        f"?Appl_Type={at}&Appl_No={an}"
    )


def url_orange_producto_ancla(
    appl_type: str | None,
    appl_no: str | None,
    product_no: str | None = None,
    *,
    ob_anchor: str | None = None,
) -> str | None:
    """Ficha del producto en Orange Book (results_product.cfm#ancla FDA)."""
    base = url_orange_producto(appl_type, appl_no)
    if not base:
        return None
    anchor = str(ob_anchor or "").strip()
    if anchor:
        return f"{base}#{anchor}"
    pn = str(product_no or "").strip()
    if not pn:
        return base
    anchor = pn.lstrip("0") or pn
    return f"{base}#{anchor}"


_OB_ANCHOR_CACHE: dict[tuple[str, str], dict[str, str]] = {}


def _anclas_orange_producto(
    appl_type: str,
    appl_no: str,
    sess: requests.Session,
) -> dict[str, str]:
    """Product_No → id de ancla en results_product.cfm (p. ej. 001 → 36948)."""
    at = str(appl_type or "").strip().upper()
    an = str(appl_no or "").strip()
    if an.isdigit():
        an = an.zfill(6)
    key = (at, an)
    if key in _OB_ANCHOR_CACHE:
        return _OB_ANCHOR_CACHE[key]
    url = url_orange_producto(at, an)
    if not url:
        return {}
    mapping: dict[str, str] = {}
    try:
        r = sess.get(url, timeout=45)
        r.raise_for_status()
        html = r.text
        for m in re.finditer(
            r'href="#(\d+)".*?Product Number:</strong>&nbsp;(\d+)',
            html,
            re.S | re.I,
        ):
            anchor, pno = m.group(1), m.group(2)
            mapping[pno] = anchor
            mapping[pno.lstrip("0") or pno] = anchor
    except Exception:
        return {}
    if mapping:
        _OB_ANCHOR_CACHE[key] = mapping
    return mapping


def url_orange_patent_info(
    appl_type: str | None,
    appl_no: str | None,
    product_no: str | None = None,
) -> str | None:
    """Ficha FDA con la tabla real de patentes del producto (Orange Book)."""
    at = str(appl_type or "").strip().upper()
    an = str(appl_no or "").strip()
    pn = str(product_no or "").strip() or "001"
    if not at or not an:
        return None
    if an.isdigit():
        an = an.zfill(6)
    if pn.isdigit():
        pn = pn.zfill(3)
    # Appl_type (t minúscula) es el parámetro que usa patent_info.cfm
    return (
        "https://www.accessdata.fda.gov/scripts/cder/ob/patent_info.cfm"
        f"?Product_No={pn}&Appl_No={an}&Appl_type={at}"
    )


def url_orange_patente(patent_no: str | None) -> str | None:
    pn = str(patent_no or "").replace(",", "").strip()
    if not pn:
        return None
    return (
        "https://www.accessdata.fda.gov/scripts/cder/ob/results_patent.cfm"
        f"?Patent_No={pn}"
    )


def url_purple_producto(bla: str | None) -> str | None:
    b = str(bla or "").strip()
    if not b:
        return None
    return f"https://purplebooksearch.fda.gov/index.cfm?event=productdetails&blaNo={b}"


def format_patent_no_us_comma(patent_no: str | None) -> str | None:
    raw = re.sub(r",", "", str(patent_no or "").strip())
    raw = re.sub(r"\*PED$", "", raw, flags=re.I)
    if not raw:
        return None
    if not re.fullmatch(r"\d+", raw):
        return str(patent_no or "").strip() or None
    return re.sub(r"\B(?=(\d{3})+(?!\d))", ",", raw)


def url_purple_patent_list_patente(patent_no: str | None) -> str | None:
    """Patent List con fragmento de texto (resalta el nº en la tabla FDA)."""
    display = format_patent_no_us_comma(patent_no)
    if not display:
        return None
    return f"{PURPLE_PATENTS_URL}#:~:text={quote(display)}"


def url_google_patente(patent_no: str | None) -> str | None:
    pn = str(patent_no or "").replace(",", "").strip()
    if not pn.isdigit():
        return None
    return f"https://patents.google.com/patent/US{pn}"


def _parse_fecha(raw: str | None) -> date | None:
    if not raw:
        return None
    s = str(raw).strip().replace(",", "")
    if not s or s.upper() in ("N/A", "NA", "-"):
        return None
    # Orange Book: Mar 14, 2034 | Purple: January 4, 2031 | already without comma ok
    s2 = str(raw).strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(s2.replace("  ", " "), fmt).date()
        except ValueError:
            continue
    return None


def _estado_fecha(d: date | None, hoy: date | None = None) -> str:
    if d is None:
        return "sin_fecha"
    hoy = hoy or date.today()
    if d < hoy:
        return "expirada"
    if d == hoy:
        return "vence_hoy"
    return "vigente"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*"})
    return s


def asegurar_orange_book(fresh: bool = False, sess: requests.Session | None = None) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    zpath = CACHE / "orange_book.zip"
    if zpath.exists() and zpath.stat().st_size > 1000 and not fresh:
        return zpath
    sess = sess or _session()
    r = sess.get(ORANGE_ZIP_URL, timeout=120)
    r.raise_for_status()
    zpath.write_bytes(r.content)
    return zpath


def _leer_ob_txt(zpath: Path, name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zpath) as zf:
        raw = zf.read(name).decode("latin-1", errors="replace")
    reader = csv.DictReader(io.StringIO(raw), delimiter="~")
    return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


# Sales comunes: no deben bastar solos para emparejar (evita HCl de otro INN).
_SALT_TOKENS = frozenset(
    {
        "hydrochloride",
        "sodium",
        "potassium",
        "calcium",
        "magnesium",
        "acetate",
        "mesylate",
        "maleate",
        "fumarate",
        "succinate",
        "tartrate",
        "citrate",
        "phosphate",
        "sulfate",
        "sulphate",
        "bromide",
        "chloride",
        "hydrate",
        "monohydrate",
        "dihydrate",
        "trihydrate",
        "anhydrous",
    }
)


def _lista_es_combinado(aliases_norm: list[str]) -> bool:
    """Igual idea que EMA: combo en lista suele llevar '/' (o ';' raro)."""
    return any("/" in (a or "") or ";" in (a or "") for a in aliases_norm)


def _ingredient_es_combinado(ingredient: str) -> bool:
    """Orange Book / Drugs@FDA: varios APIs van separados por ';'."""
    return ";" in (ingredient or "")


def _core_token(alias: str) -> str | None:
    for t in (alias or "").split():
        if t and t not in _SALT_TOKENS and len(t) >= 5:
            return t
    return None


def _match_ingredient(ingredient: str, aliases: list[str]) -> bool:
    ing = norm(ingredient)
    if not ing:
        return False
    for a in aliases:
        if len(a) < 4 or a in _SALT_TOKENS:
            continue
        # Límites de palabra: evita "aloxi" ⊂ "raloxifene"
        if re.search(rf"(^| ){re.escape(a)}( |$)", ing):
            return True
        if len(ing) >= 6 and re.search(rf"(^| ){re.escape(ing)}( |$)", a):
            return True
        tok = _core_token(a)
        if tok and re.search(rf"(^| ){re.escape(tok)}( |$)", ing):
            return True
    return False


def patentes_orange_book(
    aliases_norm: list[str],
    *,
    fresh: bool = False,
    sess: requests.Session | None = None,
    permitir_combinados: bool | None = None,
) -> dict[str, Any]:
    """
    Patentes + exclusividades + productos del Orange Book para los aliases.

    Si la lista DAMAC es un solo principio (sin '/' ni ';'), se ignoran filas
    Ingredient con ';' (combinaciones tipo AKYNZEO: NETUPITANT; PALONOSETRON…).
    """
    sess = sess or _session()
    zpath = asegurar_orange_book(fresh=fresh, sess=sess)
    products = _leer_ob_txt(zpath, "products.txt")
    patents = _leer_ob_txt(zpath, "patent.txt")
    exclus = _leer_ob_txt(zpath, "exclusivity.txt")

    lista_combo = (
        bool(permitir_combinados)
        if permitir_combinados is not None
        else _lista_es_combinado(aliases_norm)
    )

    apps: set[tuple[str, str]] = set()
    productos: list[dict[str, Any]] = []
    for p in products:
        ing_raw = p.get("Ingredient") or ""
        if _ingredient_es_combinado(ing_raw) and not lista_combo:
            continue
        if not _match_ingredient(ing_raw, aliases_norm):
            continue
        at, an = p.get("Appl_Type") or "", p.get("Appl_No") or ""
        apps.add((at, an))
        productos.append(
            {
                "ingredient": p.get("Ingredient"),
                "trade_name": p.get("Trade_Name"),
                "applicant": p.get("Applicant_Full_Name") or p.get("Applicant"),
                "strength": p.get("Strength"),
                "df_route": p.get("DF;Route"),
                "appl_type": at,
                "appl_no": an,
                "product_no": p.get("Product_No"),
                "te_code": p.get("TE_Code"),
                "approval_date": p.get("Approval_Date"),
                "rld": p.get("RLD"),
                "rs": p.get("RS"),
                "type": p.get("Type"),
                "clase": (
                    "generico_anda"
                    if at == "A"
                    else ("marca_nda" if at == "N" else at or "otro")
                ),
                "fuente_url": url_orange_producto(at, an) or ORANGE_SEARCH,
            }
        )

    anchor_maps: dict[tuple[str, str], dict[str, str]] = {}
    for at, an in apps:
        anchor_maps[(at, an)] = _anclas_orange_producto(at, an, sess)
    for prod in productos:
        at, an = prod.get("appl_type") or "", prod.get("appl_no") or ""
        pno = prod.get("product_no") or ""
        anchors = anchor_maps.get((at, an), {})
        ob_anchor = anchors.get(pno) or anchors.get(str(pno).lstrip("0") or pno)
        if ob_anchor:
            prod["ob_anchor"] = ob_anchor
            prod["fuente_url"] = url_orange_producto_ancla(at, an, pno, ob_anchor=ob_anchor) or prod["fuente_url"]

    hoy = date.today()
    prod_meta: dict[tuple[str, str, str], dict[str, str]] = {}
    for p in products:
        at0, an0 = p.get("Appl_Type") or "", p.get("Appl_No") or ""
        pno = p.get("Product_No") or ""
        meta = {
            "trade_name": p.get("Trade_Name") or "",
            "ingredient": p.get("Ingredient") or "",
            "strength": p.get("Strength") or "",
            "df_route": p.get("DF;Route") or "",
            "applicant": p.get("Applicant_Full_Name") or p.get("Applicant") or "",
        }
        prod_meta[(at0, an0, pno)] = meta
        prod_meta.setdefault((at0, an0, ""), meta)

    pats_out: list[dict[str, Any]] = []
    for row in patents:
        key = (row.get("Appl_Type") or "", row.get("Appl_No") or "")
        if key not in apps:
            continue
        exp = _parse_fecha(row.get("Patent_Expire_Date_Text"))
        at, an = row.get("Appl_Type") or "", row.get("Appl_No") or ""
        pno = row.get("Product_No") or "001"
        pn = row.get("Patent_No")
        meta = prod_meta.get((at, an, pno)) or prod_meta.get((at, an, "")) or {}
        anchors = anchor_maps.get((at, an), {})
        ob_anchor = anchors.get(pno) or anchors.get(str(pno).lstrip("0") or pno)
        product_url = (
            url_orange_producto_ancla(at, an, pno, ob_anchor=ob_anchor)
            or ORANGE_SEARCH
        )
        info_url = url_orange_patent_info(at, an, pno) or product_url
        pats_out.append(
            {
                "fuente": "orange_book",
                "appl_type": at,
                "appl_no": an,
                "product_no": pno,
                "ob_anchor": ob_anchor,
                "patent_no": pn,
                "ingredient": meta.get("ingredient") or None,
                "proprietary_name": meta.get("trade_name") or None,
                "strength": meta.get("strength") or None,
                "df_route": meta.get("df_route") or None,
                "applicant": meta.get("applicant") or None,
                "expiration_text": row.get("Patent_Expire_Date_Text"),
                "expiration_date": exp.isoformat() if exp else None,
                "estado": _estado_fecha(exp, hoy),
                "drug_substance": bool(row.get("Drug_Substance_Flag")),
                "drug_product": bool(row.get("Drug_Product_Flag")),
                "use_code": row.get("Patent_Use_Code"),
                "delist": bool(row.get("Delist_Flag")),
                "submission_date": row.get("Submission_Date"),
                "fuente_url": product_url,
                "detalle_producto_url": product_url,
                "patent_url": product_url,
                "patent_info_url": info_url,
                "google_patent_url": url_google_patente(pn),
            }
        )

    excl_out: list[dict[str, Any]] = []
    for row in exclus:
        key = (row.get("Appl_Type") or "", row.get("Appl_No") or "")
        if key not in apps:
            continue
        exp = _parse_fecha(row.get("Exclusivity_Date"))
        excl_out.append(
            {
                "fuente": "orange_book",
                "appl_type": row.get("Appl_Type"),
                "appl_no": row.get("Appl_No"),
                "product_no": row.get("Product_No"),
                "code": row.get("Exclusivity_Code"),
                "expiration_text": row.get("Exclusivity_Date"),
                "expiration_date": exp.isoformat() if exp else None,
                "estado": _estado_fecha(exp, hoy),
                "fuente_url": ORANGE_SEARCH,
            }
        )

    pats_out.sort(key=lambda x: (x.get("estado") != "vigente", x.get("expiration_date") or "9999"))
    excl_out.sort(key=lambda x: (x.get("estado") != "vigente", x.get("expiration_date") or "9999"))

    vigentes = [p for p in pats_out if p["estado"] == "vigente"]
    expiradas = [p for p in pats_out if p["estado"] == "expirada"]
    prox = None
    if vigentes:
        prox = min(vigentes, key=lambda x: x.get("expiration_date") or "9999").get("expiration_text")

    return {
        "productos": productos,
        "patentes": pats_out,
        "exclusividades": excl_out,
        "patentes_vigentes": len(vigentes),
        "patentes_expiradas": len(expiradas),
        "patente_proxima": prox,
        "fuente_url": ORANGE_SEARCH,
        "archivo": str(zpath.name),
    }


def asegurar_purple_patents(fresh: bool = False, sess: requests.Session | None = None) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "purple_book_patents.html"
    if path.exists() and path.stat().st_size > 1000 and not fresh:
        return path
    sess = sess or _session()
    r = sess.get(PURPLE_PATENTS_URL, timeout=90)
    r.raise_for_status()
    path.write_text(r.text, encoding="utf-8")
    return path


def _cells(tr: str) -> list[str]:
    out = []
    for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.I | re.S):
        txt = re.sub(r"<[^>]+>", " ", c)
        txt = re.sub(r"\s+", " ", txt).strip()
        out.append(txt)
    return out


def patentes_purple_book(
    aliases_norm: list[str],
    *,
    fresh: bool = False,
    sess: requests.Session | None = None,
) -> dict[str, Any]:
    path = asegurar_purple_patents(fresh=fresh, sess=sess)
    html = path.read_text(encoding="utf-8", errors="replace")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I | re.S)
    hoy = date.today()
    pats: list[dict[str, Any]] = []
    for tr in rows[1:]:
        c = _cells(tr)
        if len(c) < 6:
            continue
        bla, applicant, brand, proper, patent_no, exp_txt = c[0], c[1], c[2], c[3], c[4], c[5]
        blob = norm(f"{brand} {proper}")
        if not any(a and (a in blob or blob.startswith(a) or f" {a} " in f" {blob} ") for a in aliases_norm if len(a) >= 4):
            # también sufijo biosimilar en proper
            if not any(blob.startswith(a + "-") or blob.startswith(a + " ") for a in aliases_norm if len(a) >= 4):
                continue
        exp = _parse_fecha(exp_txt)
        patent_clean = patent_no.replace(",", "").strip()
        producto_url = url_purple_producto(bla)
        patent_list_url = url_purple_patent_list_patente(patent_clean) or PURPLE_PATENTS_URL
        pats.append(
            {
                "fuente": "purple_book",
                "bla_number": bla,
                "applicant": applicant,
                "proprietary_name": brand,
                "proper_name": proper,
                "patent_no": patent_clean,
                "patent_no_display": format_patent_no_us_comma(patent_clean),
                "expiration_text": exp_txt,
                "expiration_date": exp.isoformat() if exp else None,
                "estado": _estado_fecha(exp, hoy),
                "fuente_url": patent_list_url,
                "detalle_producto_url": producto_url,
                "patent_url": patent_list_url,
                "google_patent_url": url_google_patente(patent_clean),
            }
        )
    pats.sort(key=lambda x: (x.get("estado") != "vigente", x.get("expiration_date") or "9999"))
    vigentes = [p for p in pats if p["estado"] == "vigente"]
    expiradas = [p for p in pats if p["estado"] == "expirada"]
    prox = None
    if vigentes:
        prox = min(vigentes, key=lambda x: x.get("expiration_date") or "9999").get("expiration_text")
    return {
        "patentes": pats,
        "patentes_vigentes": len(vigentes),
        "patentes_expiradas": len(expiradas),
        "patente_proxima": prox,
        "fuente_url": PURPLE_PATENTS_URL,
    }
