"""
Scraper BR · Panvel (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/br_panvel.py
    python scrapper/br_panvel.py --fresh

El proxy corporativo suele categorizar panvel.com como Online Shopping (403).
Sin acceso vivo remata caché local (mismo patrón que Farmacity).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "panvel"
BASE = "https://www.panvel.com"


def main() -> int:
    return ejecutar(
        titulo=" BR Panvel → medicamentos_altos_costos_america",
        pais="Brasil",
        farmacia="Panvel",
        moneda="BRL",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
