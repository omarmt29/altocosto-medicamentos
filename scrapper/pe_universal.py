"""Scraper PE · Farmacia Universal (VTEX)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "universal_pe"
BASE = "https://www.farmaciauniversal.com"


def main() -> int:
    return ejecutar(
        titulo=" PE Farmacia Universal → medicamentos_altos_costos_america",
        pais="Perú",
        farmacia="Farmacia Universal",
        moneda="PEN",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
