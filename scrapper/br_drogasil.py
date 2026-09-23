"""
Scraper BR · Drogasil (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/br_drogasil.py
    python scrapper/br_drogasil.py --fresh

Desde este datacenter Akamai suele responder 403; en ese caso remata caché local.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "drogasil"
BASE = "https://www.drogasil.com.br"


def main() -> int:
    return ejecutar(
        titulo=" BR Drogasil → medicamentos_altos_costos_america",
        pais="Brasil",
        farmacia="Drogasil",
        moneda="BRL",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
