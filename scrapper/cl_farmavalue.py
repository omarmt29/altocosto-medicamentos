"""Scraper CL · FarmaValue (API cl-app.3c.group)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.farmavalue_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmavalue_cl_catalogo.json"
API = "https://cl-app.3c.group/api/v1/producto"
URL_BASE = "https://www.farmavalue.com/cl/products"


def main() -> int:
    return ejecutar(
        titulo=" CL FarmaValue → medicamentos_altos_costos_america",
        pais="Chile",
        farmacia="FarmaValue",
        moneda="CLP",
        api=API,
        url_base=URL_BASE,
        cache_path=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
