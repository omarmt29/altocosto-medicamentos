"""
Scraper RD · farmacias.do → P_aguila.medicamentos_altos_costos_america

Integra el catálogo público de farmacias.do usando su sitemap de productos,
extrae detalle desde HTML/JSON-LD y cruza contra la lista DAMAC/FOMAC.

Regla operativa:
    - Match claro por alias/DCI + detalle usable => calidad "ok"
    - Match por marca o con detalle parcial/ambiguo => calidad "revisar"
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
import unicodedata
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from marcas import aliases_de_marcas  # noqa: E402
from scrapper.ficha import laboratorio_de, parse_ficha  # noqa: E402
from scrapper.matching import clasificar, medicamentos_que_pegan, norm  # noqa: E402
from scrapper.repositorio import (  # noqa: E402
    asegurar_tabla,
    contar,
    guardar_filas,
    purgar_obsoletos_fuente,
)
from db import engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmacias_do"
URLS_CACHE = CACHE / "urls_productos.json"
REPORT_PATH = ROOT / "docs" / "faltantes_digemaps_fuentes.csv"
SITEMAP_INDEX = "https://farmacias.do/sitemap.xml"
PAIS = "República Dominicana"
FARMACIA = "farmacias.do"  # fallback si el offer no trae seller
FUENTE_HOST = "farmacias.do"
MONEDA = "DOP"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 40
PAUSA = 0.15


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-DO,es;q=0.9,en;q=0.8",
        }
    )
    return s


def _json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _norm_basic(texto: Any) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().replace("®", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _slug_tokens(texto: str) -> set[str]:
    toks = set()
    for trozo in re.split(r"[-_/]+", texto):
        t = _norm_basic(trozo)
        if len(t) >= 4:
            toks.add(t)
    return toks


def candidate_terms() -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for med in MEDICAMENTOS:
        for raw in list(med["aliases"]) + aliases_de_marcas(int(med["n"])):
            t = _norm_basic(raw)
            if len(t) < 4 or t in seen:
                continue
            seen.add(t)
            out.append(t)
    for row in seeds_reporte_rd():
        for raw in (row.get("csv_marca"), row.get("csv_dci"), row.get("dci_lista")):
            t = _norm_basic(raw)
            if len(t) < 4 or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out


@lru_cache(maxsize=1)
def seeds_reporte_rd() -> list[dict[str, str]]:
    if not REPORT_PATH.exists():
        return []
    meds_por_nombre = {_norm_basic(m["nombre"]): m for m in MEDICAMENTOS}
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    with REPORT_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("pais_faltante") or "").strip() != PAIS:
                continue
            dci_lista = (row.get("dci_lista") or "").strip()
            med = meds_por_nombre.get(_norm_basic(dci_lista))
            if not med:
                continue
            csv_marca = (row.get("csv_marca") or "").strip()
            csv_dci = (row.get("csv_dci") or "").strip()
            key = (dci_lista, csv_marca, csv_dci)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "dci_lista": dci_lista,
                    "csv_marca": csv_marca,
                    "csv_dci": csv_dci,
                    "n_lista": str(med["n"]),
                }
            )
    return out


def obtener_urls_productos(s: requests.Session, *, forzar: bool) -> list[str]:
    if not forzar and URLS_CACHE.exists() and URLS_CACHE.stat().st_size > 20:
        data = json.loads(URLS_CACHE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            print(f"URLs farmacias.do en caché: {len(data)}")
            return [str(x) for x in data]

    print("Descargando sitemap farmacias.do …")
    r = s.get(SITEMAP_INDEX, timeout=TIMEOUT)
    r.raise_for_status()
    sitemaps = re.findall(r"<loc>(https://farmacias\.do/sitemap-products-[^<]+\.xml)</loc>", r.text)
    if not sitemaps:
        sitemaps = [f"https://farmacias.do/sitemap-products-{i}.xml" for i in range(1, 12)]

    urls: set[str] = set()
    for sm in sitemaps:
        try:
            rr = s.get(sm, timeout=TIMEOUT)
            if rr.status_code != 200:
                continue
            hits = re.findall(r"<loc>(https://farmacias\.do/producto/[^<]+)</loc>", rr.text)
            if hits:
                urls.update(hits)
                print(f"  {sm.rsplit('/', 1)[-1]}: {len(hits)}")
        except Exception as exc:
            print(f"  {sm}: error {exc}")
    out = sorted(urls)
    _json_dump(URLS_CACHE, out)
    print(f"URLs totales farmacias.do: {len(out)}")
    return out


def filtrar_urls_candidatas(urls: list[str]) -> list[str]:
    terms = candidate_terms()
    candidatos: list[str] = []
    seen: set[str] = set()
    for url in urls:
        path = url.rstrip("/").rsplit("/", 1)[-1]
        slug_text = _norm_basic(path.replace("-", " "))
        slug_toks = _slug_tokens(path)
        ok = False
        for term in terms:
            if term in slug_text:
                ok = True
                break
            partes = term.split()
            if len(partes) == 1 and partes[0] in slug_toks:
                ok = True
                break
        if ok and url not in seen:
            seen.add(url)
            candidatos.append(url)
    return candidatos


def extraer_jsonld_products(html: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        cola = data if isinstance(data, list) else [data]
        while cola:
            item = cola.pop(0)
            if isinstance(item, list):
                cola.extend(item)
                continue
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "Product":
                out.append(item)
            if isinstance(item.get("@graph"), list):
                cola.extend(item["@graph"])
    return out


def parse_precio(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    s = str(valor).strip().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    n = float(m.group(1))
    return n if n > 0 else None


def _strip_tags(html: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = txt.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", txt).strip()


def extraer_principio_activo(html: str) -> str:
    m = re.search(
        r"(?is)principio\s+activo\s*:?\s*(?:</[^>]+>\s*)*(?:<[^>]+>\s*)*([^<]{3,200})",
        html,
    )
    if m:
        return _strip_tags(m.group(1)).rstrip("→").strip()
    m = re.search(r'<a[^>]+href=["\'][^"\']*/medicamento/[^"\']*["\'][^>]*>(.*?)</a>', html, re.I | re.S)
    if m:
        return _strip_tags(m.group(1)).rstrip("→").strip()
    return ""


def extraer_laboratorio(html: str) -> str:
    """Solo etiquetas explícitas de marca/laboratorio (no prosa ni seller)."""
    patrones = [
        r'(?is)<[^>]*>(?:\s*)(?:marca|laboratorio|fabricante|laboratorio\s+fabricante)\s*:?\s*</[^>]+>\s*<[^>]+>\s*([^<]{2,120})',
        r'(?is)(?:marca|laboratorio|fabricante)\s*:\s*</?(?:span|div|strong|b|p)[^>]*>\s*([^<]{2,120})',
        r'(?is)"brand"\s*:\s*(?:\{\s*"@type"\s*:\s*"[^"]+"\s*,\s*)?"name"\s*:\s*"([^"]{2,120})"',
        r'(?is)"brand"\s*:\s*"([^"]{2,120})"',
    ]
    for pat in patrones:
        m = re.search(pat, html)
        if not m:
            continue
        txt = _strip_tags(m.group(1)).strip(" :-·|")
        if laboratorio_parece_valido(txt):
            return txt
    return ""


_SELLERS_O_BASURA = re.compile(
    r"(?i)\b("
    r"farmacias?(?:\s+los\s+hidalgos|\s+carol|\s+jones|\.do)?|"
    r"los\s+hidalgos|carol|qualipharma|farmavalue|farma\s*value|"
    r"plaza\s+lama|giralda|cruz\s+verde|imprenta|"
    r"y\s+dosis|comparadas\s+por|presentaciones\s+distintas|"
    r"precio\s+por\s+unidad|equivalencia\s+probable"
    r")\b"
)


def laboratorio_parece_valido(texto: Any) -> bool:
    t = str(texto or "").strip()
    if len(t) < 2 or len(t) > 120:
        return False
    if _SELLERS_O_BASURA.search(t):
        return False
    if re.search(r"(?i)^(y\s+dosis|comparadas|marca\s+y)", t):
        return False
    # Evitar frases largas de marketing
    if len(t.split()) > 6:
        return False
    return True


def normalizar_seller_farmacia(seller: Any) -> str:
    """Pasa el seller de farmacias.do al nombre de farmacia canónico (p. ej. GBC)."""
    raw = re.sub(r"\s+", " ", str(seller or "").strip())
    if not raw:
        return FARMACIA
    n = _norm_basic(raw)
    if "gbc" in n or "medicar" in n:
        return "GBC"
    if "hidalgo" in n:
        return "Los Hidalgos"
    if "carol" in n:
        return "Carol"
    if "farma" in n and "value" in n:
        return "FarmaValue"
    if "qualipharma" in n:
        return "Qualipharma"
    # Title Case suave para el resto
    return " ".join(w.capitalize() if w else w for w in raw.split())[:80]


def resolver_laboratorio(nombre: str, html_lab: str = "", ficha_lab: str | None = None) -> str | None:
    """Prioridad: lab en el título → ficha → HTML etiquetado. Nunca el seller."""
    for cand in (laboratorio_de(nombre), ficha_lab, html_lab):
        if laboratorio_parece_valido(cand):
            return str(cand).strip()[:200]
    return None


def detalle_producto(s: requests.Session, url: str) -> list[dict[str, Any]]:
    r = s.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    html = r.text
    productos = extraer_jsonld_products(html)
    if not productos:
        return []

    principio = extraer_principio_activo(html)
    laboratorio = extraer_laboratorio(html)
    fecha_dato = datetime.now().date().isoformat()
    out: list[dict[str, Any]] = []
    for data in productos:
        nombre = str(data.get("name") or "").strip()
        pid = str(data.get("sku") or data.get("productID") or data.get("gtin") or nombre)[:80]
        offers = data.get("offers") or {}
        lista_offers: list[dict[str, Any]] = []
        if isinstance(offers, dict):
            if offers.get("@type") == "AggregateOffer":
                lista_offers = [x for x in offers.get("offers", []) if isinstance(x, dict)]
            else:
                lista_offers = [offers]
        elif isinstance(offers, list):
            lista_offers = [x for x in offers if isinstance(x, dict)]
        if not lista_offers:
            lista_offers = [{}]

        offers_norm: list[dict[str, Any]] = []
        seen_offer_keys: set[tuple[str, float | None, str]] = set()
        for idx, offer in enumerate(lista_offers, start=1):
            seller = offer.get("seller") or {}
            seller_name = ""
            if isinstance(seller, dict):
                seller_name = str(seller.get("name") or "").strip()
            elif seller:
                seller_name = str(seller).strip()
            precio = parse_precio(offer.get("price"))
            disp_txt = _norm_basic(offer.get("availability") or offer.get("availabilityEnds") or "")
            # OutOfStock primero: "outofstock" no debe caer en Disponible por precio residual.
            if (
                "outofstock" in disp_txt
                or "out of stock" in disp_txt
                or "sold out" in disp_txt
                or "agotado" in disp_txt
            ):
                disp = "Agotado"
            elif (
                "instock" in disp_txt
                or "in stock" in disp_txt
                or "limitedavailability" in disp_txt
                or "preorder" in disp_txt
            ):
                disp = "Disponible"
            elif precio:
                disp = "Disponible"
            else:
                disp = "Consultar"
            offer_key = (seller_name.lower(), precio, disp)
            if offer_key in seen_offer_keys:
                continue
            seen_offer_keys.add(offer_key)
            offers_norm.append(
                {
                    "seller_name": seller_name,
                    "farmacia": normalizar_seller_farmacia(seller_name),
                    "precio": precio,
                    "disponibilidad": disp,
                }
            )
        # Una fila por farmacia/seller (mejor precio de ese seller).
        por_farmacia: dict[str, dict[str, Any]] = {}
        for of in offers_norm:
            if of["precio"] is None:
                continue
            far = of["farmacia"] or FARMACIA
            prev = por_farmacia.get(far)
            if prev is None or (of["precio"] or 0) < (prev["precio"] or 0):
                por_farmacia[far] = of
        if not por_farmacia:
            por_farmacia[FARMACIA] = {
                "seller_name": "",
                "farmacia": FARMACIA,
                "precio": None,
                "disponibilidad": "Consultar",
            }
        for of in por_farmacia.values():
            out.append(
                {
                    "id": pid,
                    "sku": pid,
                    "url": url,
                    "nombre": nombre,
                    "principio_activo_fuente": principio,
                    "laboratorio_fuente": laboratorio,  # nunca seller/farmacia
                    "farmacia": of["farmacia"],
                    "seller_name": of.get("seller_name") or "",
                    "precio": of["precio"],
                    "disponibilidad": of["disponibilidad"],
                    "fecha_dato": fecha_dato,
                }
            )
    return out


def _fake_producto(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "nombre": item.get("nombre"),
        "principios_activos": [item.get("principio_activo_fuente") or ""],
        "principios_activos_con_dosaje": [],
        "tipo_presentacion": item.get("nombre") or "",
        "palabras_clave": item.get("url") or "",
        "laboratorio": item.get("laboratorio_fuente") or "",
    }


def meds_por_marca(texto: str) -> list[dict[str, Any]]:
    blob = _norm_basic(texto)
    out: list[dict[str, Any]] = []
    for med in MEDICAMENTOS:
        aliases = aliases_de_marcas(int(med["n"]))
        if aliases and any(re.search(rf"(^| ){re.escape(a)}( |$)", blob) for a in aliases):
            out.append(med)
    return out


def meds_por_reporte(texto: str) -> list[dict[str, Any]]:
    blob = _norm_basic(texto)
    meds_por_n = {int(m["n"]): m for m in MEDICAMENTOS}
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in seeds_reporte_rd():
        try:
            n_lista = int(row["n_lista"])
        except Exception:
            continue
        med = meds_por_n.get(n_lista)
        if not med or n_lista in seen:
            continue
        terms = [
            _norm_basic(row.get("csv_marca")),
            _norm_basic(row.get("csv_dci")),
            _norm_basic(row.get("dci_lista")),
        ]
        terms = [t for t in terms if len(t) >= 4]
        if any(re.search(rf"(^| ){re.escape(t)}( |$)", blob) for t in terms):
            seen.add(n_lista)
            out.append(med)
    return out


def _obs_join(*partes: str | None) -> str | None:
    vals = [str(x).strip() for x in partes if str(x or "").strip()]
    if not vals:
        return None
    return " | ".join(vals)[:400]


def filas_para_db(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Clave: farmacia real (GBC, Carol, …) + producto + n_lista
    vistos: set[tuple[str, str, int]] = set()
    for item in items:
        nombre = str(item.get("nombre") or "").strip()
        url = str(item.get("url") or "")
        precio = item.get("precio")
        if not nombre or not precio:
            continue
        base_blob = " ".join(
            [
                nombre,
                str(item.get("principio_activo_fuente") or ""),
                str(item.get("laboratorio_fuente") or ""),
                url,
            ]
        )
        alias_hits = medicamentos_que_pegan(base_blob)
        marca_hits = meds_por_marca(base_blob)
        reporte_hits = meds_por_reporte(base_blob)
        candidatos: list[tuple[dict[str, Any], str]] = []
        seen_n: set[int] = set()
        for med in alias_hits:
            n = int(med["n"])
            if n not in seen_n:
                seen_n.add(n)
                candidatos.append((med, "alias"))
        for med in marca_hits:
            n = int(med["n"])
            if n not in seen_n:
                seen_n.add(n)
                candidatos.append((med, "marca"))
        for med in reporte_hits:
            n = int(med["n"])
            if n not in seen_n:
                seen_n.add(n)
                candidatos.append((med, "reporte"))
        if not candidatos:
            continue

        fake = _fake_producto(item)
        farmacia_fila = str(item.get("farmacia") or FARMACIA)[:80]
        # Estas farmacias tienen scraper propio; no contaminar con URL de farmacias.do
        # (mismo producto_key → dos enlaces distintos en la serie).
        if farmacia_fila in {"FarmaValue", "Carol", "Los Hidalgos", "Qualipharma"}:
            continue
        for med0, via in candidatos:
            med, calidad, obs = clasificar(med0, fake)
            n_lista = int(med["n"])
            pid = str(item.get("id") or "")
            if not pid:
                continue
            clave = (farmacia_fila, pid, n_lista)
            if clave in vistos:
                continue
            vistos.add(clave)

            detalle = bool(
                re.search(r"det\b|\*\*\*det", nombre, re.I)
                or re.search(r"det\b|\*\*\*det", pid, re.I)
                or url.rstrip("/").lower().endswith("det")
                or pid.lower().endswith("det")
            )
            ficha = parse_ficha(
                " ".join([nombre, str(item.get("principio_activo_fuente") or "")]).strip(),
                med,
                detalle=detalle,
            )
            pa_fuente = str(item.get("principio_activo_fuente") or "").strip()
            pa_norm = norm(pa_fuente)
            med_alias_ok = any(
                re.search(rf"(^| ){re.escape(norm(a))}( |$)", pa_norm)
                for a in med["aliases"]
                if len(norm(a)) >= 4
            )
            conc = ficha.get("concentracion")
            pres = ficha.get("presentacion")
            lab = resolver_laboratorio(
                nombre,
                html_lab=str(item.get("laboratorio_fuente") or ""),
                ficha_lab=ficha.get("laboratorio"),
            )
            detalle_parcial = not conc or not pres
            if via == "marca" and calidad == "ok":
                calidad = "revisar"
            if via == "marca" and not med_alias_ok:
                obs = _obs_join(obs, "Coincidencia por marca comercial; principio activo no confirmado en la fuente")
            elif via == "marca":
                obs = _obs_join(obs, "Coincidencia por marca comercial")
            if via == "reporte":
                calidad = "revisar" if calidad == "ok" else calidad
                obs = _obs_join(obs, "Coincidencia impulsada por faltantes RD del reporte Digemaps")
            if detalle_parcial:
                calidad = "revisar"
                obs = _obs_join(obs, "Concentración o presentación incompleta en farmacias.do")
            if detalle:
                obs = _obs_join(obs, "Precio al detalle (unidad), no caja")

            out.append(
                {
                    "pais": PAIS,
                    "farmacia": str(item.get("farmacia") or FARMACIA)[:80],
                    "fuente_url": url[:500],
                    "id_producto_farmacia": pid[:80],
                    "sku": str(item.get("sku") or pid)[:80],
                    "n_lista": n_lista,
                    "medicamento_lista": str(med["nombre"]),
                    "programa": str(med["programa"]),
                    "nombre_comercial": nombre[:500],
                    "principio_activo": (pa_fuente or ficha.get("principio_activo") or None),
                    "concentracion": conc or None,
                    "presentacion": pres or None,
                    "laboratorio": lab,
                    "precio": precio,
                    "moneda": MONEDA,
                    "disponibilidad": item.get("disponibilidad") or "Consultar",
                    "calidad": calidad,
                    "observacion": _obs_join(obs, ficha.get("observacion_ficha")),
                    "fecha_publicacion": None,
                    "fecha_dato": item.get("fecha_dato"),
                }
            )
    return out


def recolectar_detalles(s: requests.Session, urls: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    total = len(urls)
    for i, url in enumerate(urls, start=1):
        try:
            lote = detalle_producto(s, url)
        except Exception as exc:
            print(f"  [{i}/{total}] error {url}: {exc}")
            continue
        if lote:
            out.extend(lote)
            print(f"  [{i}/{total}] {lote[0]['nombre'][:80]}")
        elif i % 20 == 0:
            print(f"  [{i}/{total}] …")
        time.sleep(PAUSA)
    return out


def reparar_filas_existentes() -> dict[str, int]:
    """Reparsea laboratorio / concentración / presentación de filas ya guardadas."""
    asegurar_tabla()
    sql = text(
        """
        SELECT
            pais, farmacia, fuente_url, id_producto_farmacia, sku,
            n_lista, medicamento_lista, programa, nombre_comercial,
            principio_activo, concentracion, presentacion, laboratorio,
            precio, moneda, disponibilidad, calidad, observacion,
            fecha_publicacion, fecha_dato
        FROM P_aguila.medicamentos_altos_costos_america
        WHERE farmacia = :farmacia
        """
    )
    with engine().connect() as conn:
        rows = [dict(r) for r in conn.execute(sql, {"farmacia": FARMACIA}).mappings()]

    out: list[dict[str, Any]] = []
    cambios = 0
    labs_limpiados = 0
    for row in rows:
        nombre = str(row.get("nombre_comercial") or "").strip()
        if not nombre:
            continue
        detalle = bool(
            re.search(r"det\b|\*\*\*det", nombre, re.I)
            or re.search(r"det\b|\*\*\*det", str(row.get("id_producto_farmacia") or ""), re.I)
            or str(row.get("fuente_url") or "").rstrip("/").lower().endswith("det")
        )
        med = {
            "n": row.get("n_lista"),
            "nombre": row.get("medicamento_lista") or "",
            "programa": row.get("programa") or "",
            "aliases": [],
        }
        ficha = parse_ficha(nombre, med, detalle=detalle)
        lab_antes = row.get("laboratorio")
        lab = resolver_laboratorio(nombre, ficha_lab=ficha.get("laboratorio"))
        if lab_antes and not laboratorio_parece_valido(lab_antes):
            labs_limpiados += 1
        nueva = dict(row)
        nueva["concentracion"] = ficha.get("concentracion") or None
        nueva["presentacion"] = ficha.get("presentacion") or None
        nueva["laboratorio"] = lab
        if not nueva.get("principio_activo"):
            nueva["principio_activo"] = ficha.get("principio_activo")
        if (
            str(nueva.get("laboratorio") or "") != str(lab_antes or "")
            or str(nueva.get("concentracion") or "") != str(row.get("concentracion") or "")
            or str(nueva.get("presentacion") or "") != str(row.get("presentacion") or "")
        ):
            cambios += 1
        out.append(nueva)

    res = guardar_filas(out) if out else {"upserts": 0}
    print(
        f"Reparación farmacias.do: {len(out)} filas · {cambios} con cambios · "
        f"{labs_limpiados} labs inválidos limpiados"
    )
    return {"filas": len(out), "cambios": cambios, "labs_limpiados": labs_limpiados, **res}


def reparar_sellers_existentes() -> dict[str, int]:
    """Reetiqueta filas de farmacias.do con el seller real (GBC, Carol, …)."""
    asegurar_tabla()
    sql = text(
        """
        SELECT
            pais, farmacia, fuente_url, id_producto_farmacia, sku,
            n_lista, medicamento_lista, programa, nombre_comercial,
            principio_activo, concentracion, presentacion, laboratorio,
            precio, moneda, disponibilidad, calidad, observacion,
            fecha_publicacion, fecha_dato
        FROM P_aguila.medicamentos_altos_costos_america
        WHERE fuente_url LIKE :like OR farmacia = :farmacia
        """
    )
    with engine().connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                sql, {"like": f"%{FUENTE_HOST}%", "farmacia": FARMACIA}
            ).mappings()
        ]

    by_url: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        url = str(row.get("fuente_url") or "").strip()
        if not url:
            continue
        by_url.setdefault(url, []).append(row)

    s = session()
    nuevas: list[dict[str, Any]] = []
    urls_ok = 0
    for i, (url, grupo) in enumerate(by_url.items(), start=1):
        try:
            ofertas = detalle_producto(s, url)
        except Exception as exc:
            print(f"  [{i}/{len(by_url)}] error {url}: {exc}")
            continue
        if not ofertas:
            continue
        urls_ok += 1
        # Índice por precio redondeado para emparejar filas viejas
        por_precio: dict[float, list[dict[str, Any]]] = {}
        for of in ofertas:
            p = of.get("precio")
            if p is None:
                continue
            por_precio.setdefault(round(float(p), 2), []).append(of)
        for row in grupo:
            p = row.get("precio")
            try:
                pk = round(float(p), 2) if p is not None else None
            except Exception:
                pk = None
            cand = por_precio.get(pk or -1) or ofertas
            of = cand[0]
            nueva = dict(row)
            nueva["farmacia"] = str(of.get("farmacia") or FARMACIA)[:80]
            nuevas.append(nueva)
        print(
            f"  [{i}/{len(by_url)}] {ofertas[0].get('nombre', '')[:60]} → "
            + ", ".join(sorted({str(o.get('farmacia')) for o in ofertas}))
        )
        time.sleep(PAUSA)

    res = guardar_filas(nuevas) if nuevas else {"upserts": 0}
    # Quitar etiqueta vieja "farmacias.do" si ya hay filas con el seller real
    with engine().begin() as conn:
        borrados = conn.execute(
            text(
                """
                DELETE FROM P_aguila.medicamentos_altos_costos_america
                WHERE farmacia = :farmacia
                  AND fuente_url LIKE :like
                  AND EXISTS (
                    SELECT 1
                    FROM P_aguila.medicamentos_altos_costos_america t2
                    WHERE t2.fuente_url = medicamentos_altos_costos_america.fuente_url
                      AND t2.id_producto_farmacia = medicamentos_altos_costos_america.id_producto_farmacia
                      AND t2.n_lista = medicamentos_altos_costos_america.n_lista
                      AND t2.farmacia <> :farmacia
                  )
                """
            ),
            {"farmacia": FARMACIA, "like": f"%{FUENTE_HOST}%"},
        ).rowcount or 0

    print(
        f"Reparación sellers: {len(by_url)} URLs · {urls_ok} ok · "
        f"upserts={res.get('upserts', 0)} · huérfanas farmacias.do={borrados}"
    )
    return {"urls": len(by_url), "ok": urls_ok, "upserts": int(res.get("upserts") or 0), "borrados": borrados}


def main() -> int:
    if "--reparar-sellers" in sys.argv:
        print("=" * 64)
        print(" Reparar sellers farmacias.do → nombre real (GBC, …)")
        print("=" * 64)
        reparar_sellers_existentes()
        return 0

    if "--reparar" in sys.argv:
        print("=" * 64)
        print(" Reparar campos farmacias.do (lab / concentración / presentación)")
        print("=" * 64)
        reparar_filas_existentes()
        return 0

    forzar = "--fresh" in sys.argv
    limite = None
    if "--limit" in sys.argv:
        try:
            limite = int(sys.argv[sys.argv.index("--limit") + 1])
        except Exception:
            limite = None

    print("=" * 64)
    print(" RD farmacias.do → medicamentos_altos_costos_america")
    print("=" * 64)
    s = session()
    urls = obtener_urls_productos(s, forzar=forzar)
    urls = filtrar_urls_candidatas(urls)
    if limite:
        urls = urls[:limite]
    print(f"URLs candidatas a revisar: {len(urls)}")

    items = recolectar_detalles(s, urls)
    filas = filas_para_db(items)
    ok = sum(1 for f in filas if f["calidad"] == "ok")
    print(f"Lista DAMAC/FOMAC: {len(MEDICAMENTOS)} medicamentos")
    print(f"Coincidencias a guardar: {len(filas)}  (ok={ok}, revisar={len(filas) - ok})")
    tabla = asegurar_tabla()
    print(f"Tabla lista: {tabla}")
    res = guardar_filas(filas)
    borrados = 0
    if filas:
        borrados = purgar_obsoletos_fuente(
            PAIS,
            FUENTE_HOST,
            [(f["farmacia"], f["id_producto_farmacia"], f["n_lista"]) for f in filas],
        )
    by_far: dict[str, int] = {}
    for f in filas:
        by_far[f["farmacia"]] = by_far.get(f["farmacia"], 0) + 1
    far_txt = " · ".join(f"{k}={v}" for k, v in sorted(by_far.items(), key=lambda x: (-x[1], x[0])))
    print(
        f"MERGE {res['upserts']} filas · obsoletos: {borrados} · "
        f"por farmacia: {far_txt or '—'} · total tabla: {contar()}"
    )
    by_med: dict[str, int] = {}
    for f in filas:
        by_med[f["medicamento_lista"]] = by_med.get(f["medicamento_lista"], 0) + 1
    for nombre, n in sorted(by_med.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:2d}  {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
