"""
Scraper UY · Farmashop (VTEX) → P_aguila.medicamentos_altos_costos_america

El proxy corporativo suele bloquear farmashop.com.uy (Online Shopping).
Con red abierta o whitelist responde como otras tiendas VTEX.

Uso:
    python scrapper/uy_farmashop.py
    python scrapper/uy_farmashop.py --fresh
    python scrapper/uy_farmashop.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "farmashop"
# Tienda real VTEX (www.farmashop.com.uy suele redirigir / estar detrás del proxy).
BASE = "https://tienda.farmashop.com.uy"


def main() -> int:
    return ejecutar(
        titulo=" UY Farmashop → medicamentos_altos_costos_america",
        pais="Uruguay",
        farmacia="Farmashop",
        moneda="UYU",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
