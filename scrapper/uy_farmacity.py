"""
Scraper UY · Farmacity Uruguay (VTEX) → P_aguila.medicamentos_altos_costos_america

Catálogo mixto (dermocosmética + OTC). El matching estricto evita falsos
positivos (p. ej. Max Factor vs Factor VIII).

Uso:
    python scrapper/uy_farmacity.py
    python scrapper/uy_farmacity.py --fresh
    python scrapper/uy_farmacity.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmacity_uy"
BASE = "https://www.farmacity.com.uy"


def main() -> int:
    return ejecutar(
        titulo=" UY Farmacity → medicamentos_altos_costos_america",
        pais="Uruguay",
        farmacia="Farmacity UY",
        moneda="UYU",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
