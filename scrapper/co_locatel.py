"""
Scraper CO · Locatel Colombia (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/co_locatel.py
    python scrapper/co_locatel.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "locatel"
BASE = "https://www.locatelcolombia.com"


def main() -> int:
    return ejecutar(
        titulo=" CO Locatel → medicamentos_altos_costos_america",
        pais="Colombia",
        farmacia="Locatel",
        moneda="COP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
