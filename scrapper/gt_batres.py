"""
Scraper GT · Farmacias Batres (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/gt_batres.py
    python scrapper/gt_batres.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "batres_gt"
BASE = "https://www.farmaciasbatres.com.gt"


def main() -> int:
    return ejecutar(
        titulo=" GT Farmacias Batres → medicamentos_altos_costos_america",
        pais="Guatemala",
        farmacia="Farmacias Batres",
        moneda="GTQ",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
