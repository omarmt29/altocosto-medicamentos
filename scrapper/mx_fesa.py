"""
Scraper MX · Farmacias Especializadas (FESA, Magento GraphQL)
→ P_aguila.medicamentos_altos_costos_america

Farmacia de especialidad con PVP público; cubre enzimas y biológicos raros
(Fabrazyme, Cerezyme, Evrysdi, Gazyva, Blincyto, etc.).

Uso:
    python scrapper/mx_fesa.py
    python scrapper/mx_fesa.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.magento_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "fesa"
BASE = "https://www.farmaciasespecializadas.com"


def main() -> int:
    return ejecutar(
        titulo=" MX Farmacias Especializadas (FESA) → medicamentos_altos_costos_america",
        pais="México",
        farmacia="Farmacias Especializadas",
        moneda="MXN",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
