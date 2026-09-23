"""
Scraper EC · Pharmacy's (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/ec_pharmacys.py
    python scrapper/ec_pharmacys.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "pharmacys_ec"
BASE = "https://www.pharmacys.com.ec"


def main() -> int:
    return ejecutar(
        titulo=" EC Pharmacy's → medicamentos_altos_costos_america",
        pais="Ecuador",
        farmacia="Pharmacy's",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
