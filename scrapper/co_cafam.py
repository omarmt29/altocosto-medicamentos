"""
Scraper CO · Droguerías Cafam (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/co_cafam.py
    python scrapper/co_cafam.py --fresh

El proxy corporativo suele bloquear drogueriascafam.com.co (Online Shopping).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "cafam"
BASE = "https://www.drogueriascafam.com.co"


def main() -> int:
    return ejecutar(
        titulo=" CO Droguerías Cafam → medicamentos_altos_costos_america",
        pais="Colombia",
        farmacia="Droguerías Cafam",
        moneda="COP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
