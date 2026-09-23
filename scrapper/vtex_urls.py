"""URLs públicas de producto en tiendas VTEX (PDP, no API JSON)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# www.siman.com es solo selector de país; la tienda vive en {cc}.siman.com
SIMAN_CC_POR_PAIS: dict[str, str] = {
    "el salvador": "sv",
    "guatemala": "gt",
    "nicaragua": "ni",
    "costa rica": "cr",
    "honduras": "gt",  # sin subdominio hn; misma ficha VTEX en gt.siman.com
}


def _norm_pais_blob(pais: str | None) -> str:
    import unicodedata

    s = unicodedata.normalize("NFKD", str(pais or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def siman_cc_pais(pais: str | None) -> str | None:
    blob = _norm_pais_blob(pais)
    for needle, cc in SIMAN_CC_POR_PAIS.items():
        if needle in blob:
            return cc
    return None


def es_farmacia_siman(farmacia: str | None, base: str | None = None, url: str | None = None) -> bool:
    blob = f"{farmacia or ''} {base or ''} {url or ''}".lower()
    return "siman" in blob


def base_siman_pdp(
    pais: str | None,
    farmacia: str | None = None,
    default_base: str | None = None,
) -> str:
    if not es_farmacia_siman(farmacia, default_base):
        return str(default_base or "").rstrip("/")
    cc = siman_cc_pais(pais)
    if cc:
        return f"https://{cc}.siman.com"
    return str(default_base or "https://www.siman.com").rstrip("/")


def corregir_url_siman(
    url: str | None,
    pais: str | None = None,
    farmacia: str | None = None,
) -> str:
    """Reemplaza www.siman.com por el subdominio del país (sv, gt, ni, cr…)."""
    u = str(url or "").strip()
    if not u or "siman.com" not in u.lower():
        return u
    if re.search(r"https?://[a-z]{2}\.siman\.com", u, re.I):
        return u
    cc = siman_cc_pais(pais)
    if not cc and es_farmacia_siman(farmacia, url=u):
        cc = "sv"
    if not cc:
        return u
    return re.sub(r"https?://(?:www\.)?siman\.com", f"https://{cc}.siman.com", u, flags=re.I)


_BASE_POR_FARMACIA: list[tuple[str, str]] = [
    ("siman", "https://www.siman.com"),
    ("farmacity", "https://www.farmacity.com"),
    ("paguemenos", "https://www.paguemenos.com.br"),
    ("locatel", "https://www.locatelcolombia.com"),
    ("farmashop", "https://tienda.farmashop.com.uy"),
    ("cruz azul", "https://www.farmaciascruzazul.ec"),
    ("pharmacy", "https://www.pharmacys.com.ec"),
    ("farmacias batres", "https://www.farmaciasbatres.com.gt"),
    ("galeno", "https://www.farmaciasgaleno.com.gt"),
    ("fischel", "https://www.farmaciasfischel.com"),
    ("kolbi", "https://www.kolbi.cr"),
    ("san pablo", "https://www.farmaciasanpablo.com.mx"),
    ("similares", "https://www.farmaciasdesimilares.com"),
    ("carulla", "https://www.carulla.com"),
    ("cafam", "https://www.cafam.com.co"),
    ("la rebaja", "https://www.larebajavirtual.com"),
    ("droga raia", "https://www.drogaraia.com.br"),
    ("drogasil", "https://www.drogasil.com.br"),
    ("panvel", "https://www.panvel.com"),
]


def url_pdp(base: str, prod: dict[str, Any]) -> str | None:
    link = str(prod.get("link") or "").strip()
    if link.startswith("http"):
        return link[:500]
    slug = str(prod.get("linkText") or "").strip()
    if slug:
        return f"{base.rstrip('/')}/{slug}/p"[:500]
    return None


def es_url_api_interna(url: str | None) -> bool:
    u = str(url or "").strip().lower()
    if not u:
        return False
    if u.startswith("datos/") or u.endswith(".json"):
        return True
    if "algolia.net" in u:
        return True
    return "/api/catalog_system/" in u


def base_por_farmacia(farmacia: str | None, pais: str | None = None) -> str | None:
    if es_farmacia_siman(farmacia):
        return base_siman_pdp(pais, farmacia)
    blob = f"{farmacia or ''} {pais or ''}".lower()
    for needle, base in _BASE_POR_FARMACIA:
        if needle in blob:
            return base
    return None


def slug_desde_api_vtex(url: str) -> str | None:
    try:
        path = urlparse(url).path
    except Exception:
        return None
    m = re.search(r"/products/search/([^/]+)/p/?$", path, re.I)
    if not m:
        return None
    return m.group(1).strip() or None


def product_id_desde_api_vtex(url: str) -> str | None:
    try:
        qs = parse_qs(urlparse(url).query)
    except Exception:
        return None
    for raw in qs.get("fq") or []:
        m = re.search(r"productId:(\d+)", str(raw), re.I)
        if m:
            return m.group(1)
    return None


def product_id_desde_slug_pdp(url: str | None) -> str | None:
    """VTEX suele terminar el slug con el productId: …-823461040/p."""
    m = re.search(r"-(\d+)/p/?(?:\?|#|$)", str(url or ""), re.I)
    return m.group(1) if m else None


def url_busqueda_vtex(base: str, nombre: str | None) -> str | None:
    q = str(nombre or "").strip()
    if len(q) < 4:
        return None
    from urllib.parse import quote

    return f"{str(base or '').rstrip('/')}/s?ft={quote(q)}"[:500]


def url_siman_publica(
    url: str | None,
    *,
    pais: str | None,
    farmacia: str | None = None,
    id_producto: str | None = None,
    nombre_comercial: str | None = None,
) -> str | None:
    """PDP regional si el SKU existe en esa tienda; si no, búsqueda en la tienda."""
    if not es_farmacia_siman(farmacia, url=url):
        u = str(url or "").strip()
        return u or None

    base = base_siman_pdp(pais, farmacia)
    u = str(url or "").strip()

    pid = product_id_desde_slug_pdp(u) or product_id_desde_api_vtex(u)
    if not pid and id_producto and str(id_producto).isdigit() and len(str(id_producto)) >= 7:
        pid = str(id_producto).strip()

    if pid:
        resuelta = resolver_pdp_vtex(base, pid)
        if resuelta:
            return corregir_url_siman(resuelta, pais, farmacia)[:500]

    busqueda = url_busqueda_vtex(base, nombre_comercial)
    if busqueda:
        return busqueda
    return corregir_url_siman(u, pais, farmacia) if u else None


def producto_en_tienda_siman(
    pais: str | None,
    product_id: str | None,
    *,
    farmacia: str | None = "Siman",
    base: str | None = None,
) -> bool:
    pid = str(product_id or "").strip()
    if not pid.isdigit():
        return False
    regional = base_siman_pdp(pais, farmacia, base)
    return resolver_pdp_vtex(regional, pid) is not None


@lru_cache(maxsize=4096)
def resolver_pdp_vtex(base: str, product_id: str) -> str | None:
    """Consulta VTEX y devuelve la URL pública del producto (…/slug/p)."""
    b = str(base or "").strip().rstrip("/")
    pid = str(product_id or "").strip()
    if not b or not pid:
        return None
    try:
        r = requests.get(
            f"{b}/api/catalog_system/pub/products/search",
            params={"fq": f"productId:{pid}"},
            timeout=20,
            headers={"User-Agent": UA, "Accept": "application/json", "Referer": f"{b}/"},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        return url_pdp(b, data[0]) or None
    except Exception:
        return None


def pdp_publica(
    fuente_url: str | None,
    *,
    farmacia: str | None = None,
    pais: str | None = None,
    id_producto: str | None = None,
    nombre_comercial: str | None = None,
) -> str | None:
    """Convierte API VTEX / evidencia interna → enlace de ficha en la tienda."""
    url = str(fuente_url or "").strip()
    out: str | None = None

    if url and not es_url_api_interna(url) and url.startswith("http"):
        out = url[:500]
    else:
        base = base_por_farmacia(farmacia, pais)
        if url:
            try:
                origin = urlparse(url).netloc
                if origin and not base:
                    base = f"https://{origin}"
            except Exception:
                pass

        slug = slug_desde_api_vtex(url) if url else None
        if slug and base:
            out = f"{base.rstrip('/')}/{slug}/p"[:500]
        else:
            pid = product_id_desde_api_vtex(url) if url else None
            if not pid and id_producto and str(id_producto).isdigit():
                pid = str(id_producto).strip()

            if pid and base:
                resuelta = resolver_pdp_vtex(base, pid)
                if resuelta:
                    out = resuelta[:500]

            if not out and base and nombre_comercial:
                q = str(nombre_comercial).strip()
                if len(q) >= 4:
                    from urllib.parse import quote

                    out = f"{base.rstrip('/')}/s?ft={quote(q)}"[:500]

    if not out:
        return None
    if es_farmacia_siman(farmacia, url=out):
        siman = url_siman_publica(
            out,
            pais=pais,
            farmacia=farmacia,
            id_producto=id_producto,
            nombre_comercial=nombre_comercial,
        )
        return siman[:500] if siman else None
    return corregir_url_siman(out, pais, farmacia)[:500]


def normalizar_fila(fila: dict[str, Any]) -> dict[str, Any]:
    """Devuelve copia de fila con fuente_url pública si era API JSON."""
    out = dict(fila)
    pdp = pdp_publica(
        out.get("fuente_url"),
        farmacia=out.get("farmacia"),
        pais=out.get("pais"),
        id_producto=out.get("id_producto_farmacia"),
        nombre_comercial=out.get("nombre_comercial"),
    )
    if pdp:
        out["fuente_url"] = pdp
    return out
