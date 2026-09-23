"""Scraper GT · FarmaValue (API fg-app.3c.group)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.farmavalue_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmavalue_gt_catalogo.json"
API = "https://fg-app.3c.group/api/v1/producto"
URL_BASE = "https://www.farmavalue.com/gt/products"


def main() -> int:
    return ejecutar(
        titulo=" GT FarmaValue → medicamentos_altos_costos_america",
        pais="Guatemala",
        farmacia="FarmaValue",
        moneda="GTQ",
        api=API,
        url_base=URL_BASE,
        cache_path=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
