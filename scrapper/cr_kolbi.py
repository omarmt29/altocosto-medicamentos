"""
Scraper CR · Kölbi (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/cr_kolbi.py
    python scrapper/cr_kolbi.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "kolbi_cr"
BASE = "https://www.kolbi.cr"


def main() -> int:
    return ejecutar(
        titulo=" CR Kölbi → medicamentos_altos_costos_america",
        pais="Costa Rica",
        farmacia="Kölbi",
        moneda="CRC",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
