"""Scraper CL · Profar (Magento GraphQL) — farmacia de especialidad."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.magento_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "profar_cl"
BASE = "https://profar.cl"


def main() -> int:
    return ejecutar(
        titulo=" CL Profar → medicamentos_altos_costos_america",
        pais="Chile",
        farmacia="Profar",
        moneda="CLP",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
