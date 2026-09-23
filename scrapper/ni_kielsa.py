"""
Scraper NI · Kielsa → P_aguila.medicamentos_altos_costos_america

Uso:
    python scrapper/ni_kielsa.py
    python scrapper/ni_kielsa.py --fresh
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.kielsa_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "kielsa_ni"


def main() -> int:
    return ejecutar(
        titulo=" NI Kielsa → medicamentos_altos_costos_america",
        pais="Nicaragua",
        farmacia="Kielsa",
        moneda="NIO",
        buscador="https://buscadorni.kielsa.com:8080",
        site_base="https://www.kielsa.com.ni",
        ddp_host="www.kielsa.com.ni",
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
