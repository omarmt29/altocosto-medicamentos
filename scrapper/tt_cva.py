"""Scraper TT · CVA Pharmacy (Woo Store API bajo /pharmacy/)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.woo_store_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "cva_tt"
BASE = "https://cvalimited.com/pharmacy"


def main() -> int:
    return ejecutar(
        titulo=" TT CVA Pharmacy → medicamentos_altos_costos_america",
        pais="Trinidad y Tobago",
        farmacia="CVA Pharmacy",
        moneda="TTD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
