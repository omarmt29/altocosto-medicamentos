"""Scraper CL · Farmex (Shopify) — farmacia online."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.shopify_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmex_cl"
BASE = "https://www.farmex.cl"


def main() -> int:
    return ejecutar(
        titulo=" CL Farmex → medicamentos_altos_costos_america",
        pais="Chile",
        farmacia="Farmex",
        moneda="CLP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
