"""
Scraper SV · Farmacias San Nicolás (VTEX) → P_aguila.medicamentos_altos_costos_america

https://www.farmaciasannicolas.com/

Uso:
    python scrapper/sv_sannicolas.py
    python scrapper/sv_sannicolas.py --fresh
    python scrapper/sv_sannicolas.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "sannicolas_sv"
BASE = "https://www.farmaciasannicolas.com"


def main() -> int:
    return ejecutar(
        titulo=" SV Farmacias San Nicolás → medicamentos_altos_costos_america",
        pais="El Salvador",
        farmacia="Farmacias San Nicolás",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
