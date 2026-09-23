"""
Scraper CO · Carulla (VTEX) → P_aguila.medicamentos_altos_costos_america

Supermercado con droguería online. Cubre menos especialidad que Locatel,
pero desde este datacenter sí responde (a diferencia de Cruz Verde / Pasteur).

Uso:
    python scrapper/co_carulla.py
    python scrapper/co_carulla.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "carulla"
BASE = "https://www.carulla.com"


def main() -> int:
    return ejecutar(
        titulo=" CO Carulla → medicamentos_altos_costos_america",
        pais="Colombia",
        farmacia="Carulla",
        moneda="COP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
