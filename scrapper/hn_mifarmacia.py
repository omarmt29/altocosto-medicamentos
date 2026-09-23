"""
Scraper HN · MiFarmacia → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/hn_mifarmacia.py
    python scrapper/hn_mifarmacia.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.mifarmacia_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "mifarmacia_hn"
BASE = "https://mifarmacia.hn"


def main() -> int:
    return ejecutar(
        titulo=" HN MiFarmacia → medicamentos_altos_costos_america",
        pais="Honduras",
        farmacia="MiFarmacia",
        moneda="HNL",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
