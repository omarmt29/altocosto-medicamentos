"""Scraper GY · Pharma-X Online (Woo Store API)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.woo_store_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "pharmax_gy"
BASE = "https://pharma-xonline.com"


def main() -> int:
    return ejecutar(
        titulo=" GY Pharma-X Online → medicamentos_altos_costos_america",
        pais="Guyana",
        farmacia="Pharma-X Online",
        moneda="GYD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
