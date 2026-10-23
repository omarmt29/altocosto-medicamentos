"""Scraper US · Honeybee Health, farmacia online de pago directo."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.us_pharmacy_common import (  # noqa: E402
    cache_texto,
    json_despues_de,
    next_flight_text,
    normalizar_slug,
    persistir,
    recolectar_productos,
    session,
    url_absoluta,
)

BASE = "https://honeybeehealth.com"
SITEMAP = f"{BASE}/sitemaps/medications.xml"
CACHE = ROOT / "cache" / "farmacias" / "honeybee_us"
FARMACIA = "Honeybee Health"


def urls_sitemap(documento: str) -> list[str]:
    return re.findall(r"<loc>\s*(https://honeybeehealth\.com/drugs/[^<]+)\s*</loc>", documento, re.I)


def parsear_producto(documento: str, pagina_url: str) -> list[dict[str, Any]]:
    flight = next_flight_text(documento)
    producto = json_despues_de(flight, '"productData":{"product":')
    if not isinstance(producto, dict):
        return []
    full_name = str(producto.get("full_name") or producto.get("product_name") or "").strip()
    generic = producto.get("generic_product") or {}
    principio = generic.get("generic_name") if isinstance(generic, dict) else None
    salida: list[dict[str, Any]] = []
    for variant in producto.get("product_variants") or []:
        if not isinstance(variant, dict) or not variant.get("price"):
            continue
        fuerza = variant.get("strength") or {}
        formulacion = fuerza.get("formulation") or {} if isinstance(fuerza, dict) else {}
        fabricante = variant.get("manufacturer") or {}
        pack = variant.get("package_size")
        unidad = variant.get("unit_abbr") or "unidades"
        salida.append(
            {
                "id": variant.get("id"),
                "sku": variant.get("id"),
                "nombre": full_name,
                "principio_activo": principio,
                "concentracion": fuerza.get("name") if isinstance(fuerza, dict) else None,
                "presentacion": f"{formulacion.get('name') or 'Producto'} x {pack} {unidad}" if pack else formulacion.get("name"),
                "laboratorio": fabricante.get("name") if isinstance(fabricante, dict) else None,
                "precio": variant.get("price"),
                "url": url_absoluta(BASE, variant.get("details_page_url") or pagina_url),
                "disponibilidad": "Disponible" if variant.get("in_stock") else "Agotado",
                "observacion": "Precio directo sin seguro publicado por Honeybee Health",
            }
        )
    return salida


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session(accept="application/xml,text/xml,text/html;q=0.9")
    sitemap = cache_texto(s, SITEMAP, CACHE, forzar=forzar)
    paginas = urls_sitemap(sitemap)
    por_slug = {normalizar_slug(urlparse(url).path.rsplit("/", 1)[-1]): url for url in paginas}
    trabajo = meds if meds is not None else MEDICAMENTOS

    def proveedor(med: dict[str, Any]) -> list[dict[str, Any]]:
        aliases = {normalizar_slug(a) for a in [med.get("nombre"), *(med.get("aliases") or [])]}
        urls = {por_slug[a] for a in aliases if a in por_slug}
        encontrados: list[dict[str, Any]] = []
        for url in sorted(urls):
            try:
                documento = cache_texto(s, url, CACHE, forzar=forzar)
            except Exception as exc:
                print(f"  aviso Honeybee {url}: {exc}")
                continue
            encontrados.extend(parsear_producto(documento, url))
        return encontrados

    return recolectar_productos(farmacia=FARMACIA, meds=trabajo, proveedor=proveedor)


def main() -> int:
    forzar = "--fresh" in sys.argv
    meds = MEDICAMENTOS
    if "--fomac" in sys.argv:
        meds = [m for m in meds if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" US Honeybee Health → medicamentos_altos_costos_america")
    print("=" * 64)
    filas = recolectar(forzar=forzar, meds=meds)
    print(f"Lista: {len(meds)} · coincidencias: {len(filas)}")
    return persistir(farmacia=FARMACIA, filas=filas)


if __name__ == "__main__":
    raise SystemExit(main())
