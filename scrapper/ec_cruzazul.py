"""
Scraper EC · Cruz Azul (VTEX) → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/ec_cruzazul.py
    python scrapper/ec_cruzazul.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "cruzazul_ec"
BASE = "https://www.farmaciascruzazul.ec"


def main() -> int:
    return ejecutar(
        titulo=" EC Cruz Azul → medicamentos_altos_costos_america",
        pais="Ecuador",
        farmacia="Cruz Azul",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
