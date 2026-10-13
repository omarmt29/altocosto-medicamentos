"""Scraper CO · Farmalisto (Shopify)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.shopify_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmalisto_co"
BASE = "https://www.farmalisto.com.co"


def main() -> int:
    return ejecutar(
        titulo=" CO Farmalisto → medicamentos_altos_costos_america",
        pais="Colombia",
        farmacia="Farmalisto",
        moneda="COP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
