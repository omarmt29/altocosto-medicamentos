"""
Scraper NI · Farmacias del Ahorro (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/ni_fahorro.py
    python scrapper/ni_fahorro.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "fahorro_ni"
BASE = "https://www.farmaciasdelahorro.hn"


def main() -> int:
    return ejecutar(
        titulo=" NI Farmacias del Ahorro → medicamentos_altos_costos_america",
        pais="Nicaragua",
        farmacia="Farmacias del Ahorro",
        moneda="NIO",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
