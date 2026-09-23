"""Scraper SV · El Farmacéutico (WooCommerce Store API)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.woo_store_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "elfarmaceutico_sv"
BASE = "https://elfarmaceutico.net"


def main() -> int:
    return ejecutar(
        titulo=" SV El Farmacéutico → medicamentos_altos_costos_america",
        pais="El Salvador",
        farmacia="El Farmacéutico",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
