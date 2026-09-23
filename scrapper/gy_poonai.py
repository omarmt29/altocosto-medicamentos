"""Scraper GY · Poonai Pharmacy (Woo Store API)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.woo_store_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "poonai_gy"
BASE = "https://poonaipharmacy.gy"


def main() -> int:
    return ejecutar(
        titulo=" GY Poonai Pharmacy → medicamentos_altos_costos_america",
        pais="Guyana",
        farmacia="Poonai Pharmacy",
        moneda="GYD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
