"""
Scraper CR · Farmacias Fischel → P_aguila.medicamentos_altos_costos_america

Nota: el sitio online vigente es fischelenlinea.com (Sitefinity, sin API VTEX
pública). El wrapper VTEX histórico apunta a farmaciasfischel.com y suele
devolver 0 hits; se mantiene en cron por si reactiva catálogo VTEX.

Uso:
    python scrapper/cr_fischel.py
    python scrapper/cr_fischel.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "fischel_cr"
BASE = "https://www.farmaciasfischel.com"


def main() -> int:
    return ejecutar(
        titulo=" CR Farmacias Fischel → medicamentos_altos_costos_america",
        pais="Costa Rica",
        farmacia="Farmacias Fischel",
        moneda="CRC",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
