"""
Scraper SV · Siman (VTEX, sección Farmacia)
→ P_aguila.medicamentos_altos_costos_america

Siman es retail regional (El Salvador usa USD). Se cruza el catálogo VTEX
público de siman.com con la lista DAMAC-FOMAC.

Uso:
    python scrapper/sv_siman.py
    python scrapper/sv_siman.py --fresh
    python scrapper/sv_siman.py --cache
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.vtex_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "siman"
BASE = "https://sv.siman.com"


def main() -> int:
    return ejecutar(
        titulo=" SV Siman → medicamentos_altos_costos_america",
        pais="El Salvador",
        farmacia="Siman",
        moneda="USD",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
