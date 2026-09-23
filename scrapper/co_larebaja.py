"""
Scraper CO · La Rebaja Virtual (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/co_larebaja.py
    python scrapper/co_larebaja.py --fresh

El proxy corporativo suele bloquear larebajavirtual.com (Online Shopping).
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "larebaja"
BASE = "https://www.larebajavirtual.com"


def main() -> int:
    return ejecutar(
        titulo=" CO La Rebaja → medicamentos_altos_costos_america",
        pais="Colombia",
        farmacia="La Rebaja",
        moneda="COP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
