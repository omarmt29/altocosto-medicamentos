"""
Scraper MX · Farmacias del Ahorro (Magento GraphQL) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/mx_fahorro.py
    python scrapper/mx_fahorro.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.magento_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "fahorro"
BASE = "https://www.fahorro.com"


def main() -> int:
    return ejecutar(
        titulo=" MX Farmacias del Ahorro → medicamentos_altos_costos_america",
        pais="México",
        farmacia="Farmacias del Ahorro",
        moneda="MXN",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
