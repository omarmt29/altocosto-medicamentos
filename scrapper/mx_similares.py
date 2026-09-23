"""
Scraper MX · Farmacias Similares (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/mx_similares.py
    python scrapper/mx_similares.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "similares"
BASE = "https://www.farmaciasdesimilares.com"


def main() -> int:
    return ejecutar(
        titulo=" MX Farmacias Similares → medicamentos_altos_costos_america",
        pais="México",
        farmacia="Farmacias Similares",
        moneda="MXN",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
