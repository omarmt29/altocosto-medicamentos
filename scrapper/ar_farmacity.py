"""
Scraper AR · Farmacity (VTEX) → P_aguila.medicamentos_altos_costos_america

La red de este servidor bloquea Farmacity (categoría Online Shopping).
Sin acceso vivo se remata el caché local de búsquedas VTEX ya bajadas.

Uso:
    python scrapper/ar_farmacity.py
    python scrapper/ar_farmacity.py --fresh
    python scrapper/ar_farmacity.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmacity"
BASE = "https://www.farmacity.com"


def main() -> int:
    return ejecutar(
        titulo=" AR Farmacity → medicamentos_altos_costos_america",
        pais="Argentina",
        farmacia="Farmacity",
        moneda="ARS",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
