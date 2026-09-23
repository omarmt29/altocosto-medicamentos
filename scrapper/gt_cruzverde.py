"""Scraper GT · Cruz Verde Guatemala (API /api/products?search=)."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from scrapper.next_search_tienda import ejecutar  # noqa: E402

CACHE = ROOT / "cache" / "farmacias" / "cruzverde_gt"
BASE = "https://cruzverde.com.gt"


def main() -> int:
    return ejecutar(
        titulo=" GT Cruz Verde → medicamentos_altos_costos_america",
        pais="Guatemala",
        farmacia="Cruz Verde",
        moneda="GTQ",
        base=BASE,
        cache=CACHE,
        api_path="/api/products",
        search_param="search",
        argv=sys.argv,
        verify=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
