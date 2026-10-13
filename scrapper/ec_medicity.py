"""Scraper EC · Farmacias Medicity (VTEX / Farmaenlace)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "medicity_ec"
BASE = "https://www.farmaciasmedicity.com"


def main() -> int:
    return ejecutar(
        titulo=" EC Medicity → medicamentos_altos_costos_america",
        pais="Ecuador",
        farmacia="Medicity",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
