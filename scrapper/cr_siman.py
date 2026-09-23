"""
Scraper CR · Siman (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/cr_siman.py
    python scrapper/cr_siman.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "siman_cr"
BASE = "https://cr.siman.com"


def main() -> int:
    return ejecutar(
        titulo=" CR Siman → medicamentos_altos_costos_america",
        pais="Costa Rica",
        farmacia="Siman",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
