"""Scraper US · HealthWarehouse, farmacia online acreditada."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from lista import MEDICAMENTOS  # noqa: E402
from scrapper.us_pharmacy_common import (  # noqa: E402
    cache_texto,
    next_flight_text,
    objetos_json,
    persistir,
    recolectar_productos,
    session,
    terminos_busqueda,
    url_absoluta,
)

BASE = "https://www.healthwarehouse.com"
CACHE = ROOT / "cache" / "farmacias" / "healthwarehouse_us"
FARMACIA = "HealthWarehouse"


def parsear_busqueda(documento: str) -> list[dict[str, Any]]:
    flight = next_flight_text(documento)
    productos = objetos_json(flight, '{"__typename":"Product"')
    salida: list[dict[str, Any]] = []
    for row in productos:
        if not row.get("pharmacy") or not row.get("isActive"):
            continue
        precio = row.get("minPrice")
        if not precio:
            continue
        salida.append(
            {
                "id": row.get("id"),
                "sku": row.get("sku") or row.get("id"),
                "nombre": row.get("name"),
                "precio": precio,
                "url": url_absoluta(BASE, row.get("url")),
                "disponibilidad": "Disponible" if row.get("inStock") else "Agotado",
                "presentacion": "Precio minimo publicado",
                "observacion": "Precio 'desde' publicado por la farmacia; validar cantidad en la ficha",
                "forzar_revision": True,
            }
        )
    return salida


def recolectar(*, forzar: bool = False, meds: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    s = session()
    trabajo = meds if meds is not None else MEDICAMENTOS

    def proveedor(med: dict[str, Any]) -> list[dict[str, Any]]:
        encontrados: dict[str, dict[str, Any]] = {}
        for term in terminos_busqueda(med):
            url = f"{BASE}/search/{quote(term, safe='')}"
            try:
                documento = cache_texto(s, url, CACHE, forzar=forzar)
            except Exception as exc:
                print(f"  aviso HealthWarehouse {term!r}: {exc}")
                continue
            for producto in parsear_busqueda(documento):
                encontrados[str(producto["sku"])] = producto
            if encontrados:
                break
        return list(encontrados.values())

    return recolectar_productos(farmacia=FARMACIA, meds=trabajo, proveedor=proveedor)


def main() -> int:
    forzar = "--fresh" in sys.argv
    meds = MEDICAMENTOS
    if "--fomac" in sys.argv:
        meds = [m for m in meds if "FOMAC" in str(m["programa"])]
    print("=" * 64)
    print(" US HealthWarehouse → medicamentos_altos_costos_america")
    print("=" * 64)
    filas = recolectar(forzar=forzar, meds=meds)
    print(f"Lista: {len(meds)} · coincidencias: {len(filas)}")
    return persistir(farmacia=FARMACIA, filas=filas)


if __name__ == "__main__":
    raise SystemExit(main())
