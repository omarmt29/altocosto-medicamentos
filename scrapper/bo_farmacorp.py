"""Scraper BO · Farmacorp (Shopify).

El dominio farmacorp.com suele estar bloqueado por proxy corporativo;
la Storefront API responde en farmacorp.myshopify.com.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.shopify_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmacorp_bo"
BASE = "https://farmacorp.myshopify.com"
PUBLIC = "https://farmacorp.com"


def main() -> int:
    return ejecutar(
        titulo=" BO Farmacorp → medicamentos_altos_costos_america",
        pais="Bolivia",
        farmacia="Farmacorp",
        moneda="BOB",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
        public_base=PUBLIC,
    )


if __name__ == "__main__":
    raise SystemExit(main())
