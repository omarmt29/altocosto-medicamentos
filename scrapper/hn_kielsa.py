"""
Scraper HN · Kielsa → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/hn_kielsa.py
    python scrapper/hn_kielsa.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.kielsa_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "kielsa_hn"


def main() -> int:
    return ejecutar(
        titulo=" HN Kielsa → medicamentos_altos_costos_america",
        pais="Honduras",
        farmacia="Kielsa",
        moneda="HNL",
        buscador="https://buscador.kielsa.com:8080",
        site_base="https://kielsa.com",
        ddp_host="kielsa.com",
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
