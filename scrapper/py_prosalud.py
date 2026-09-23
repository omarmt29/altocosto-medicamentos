"""Scraper PY · Prosalud Farma (Woo Store API)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.woo_store_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "prosalud_py"
BASE = "https://prosaludfarma.com.py"


def main() -> int:
    return ejecutar(
        titulo=" PY Prosalud Farma → medicamentos_altos_costos_america",
        pais="Paraguay",
        farmacia="Prosalud Farma",
        moneda="PYG",
        base=BASE,
        cache=CACHE,
        argv=sys.argv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
