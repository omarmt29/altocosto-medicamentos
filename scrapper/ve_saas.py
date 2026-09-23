"""Scraper VE · Farmacia SAAS (VTEX)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "saas_ve"
BASE = "https://www.farmaciasaas.com"


def main() -> int:
    return ejecutar(
        titulo=" VE Farmacia SAAS → medicamentos_altos_costos_america",
        pais="Venezuela",
        farmacia="Farmacia SAAS",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
